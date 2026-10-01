# ruff: noqa: I001
# anki.collection must be imported before other anki.* submodules; importing
# anki.cards first triggers a circular import (anki.hooks -> anki.hooks_gen ->
# anki.cards.Card while anki.cards is still initialising).
import base64
import hashlib
import logging
import re
import threading
import time
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from anki.collection import Collection, StripHtmlMode
from anki.cards import CardId
from anki.decks import DeckConfigDict, DeckConfigId, DeckId
from anki.models import FieldDict, NotetypeDict, NotetypeId, TemplateDict
from anki.notes import Note, NoteId
from anki.sync_pb2 import MediaSyncStatusResponse, SyncCollectionResponse
from httpx import Client, HTTPError

from anki_connect_server.config import get_config
from anki_connect_server.sync import (
    CollectionSyncOutcome,
    CollectionSyncResult,
    DownloadReason,
    MediaSyncResult,
    SyncError,
    SyncResult,
)
from anki_connect_server.types import JsonObject

logger = logging.getLogger(__name__)

type SyncProgressCallback = Callable[[str], None]


class AnkiWrapper:
    def __init__(self, collection_path: str) -> None:
        Collection.initialize_backend_logging()
        self.collection_path = collection_path
        self.col: Collection = Collection(collection_path)
        self._closed = False
        self._collection_generation = 0
        self._sync_lock = threading.Lock()

    @property
    def collection_generation(self) -> int:
        """Incremented whenever synchronization reopens the collection."""
        return self._collection_generation

    def close(self) -> None:
        if not self._closed:
            try:
                self.col.close()
            except Exception:
                logger.warning(
                    "Failed to close the Anki collection cleanly; "
                    "the database lock may persist until the process exits.",
                    exc_info=True,
                )
            finally:
                self._closed = True

    def _reopen_collection(self) -> None:
        if not self._closed:
            self.close()
        logger.debug("Reopening Anki collection at %s", self.collection_path)
        self.col = Collection(self.collection_path)
        self._closed = False
        self._collection_generation += 1

    def abort_sync(self) -> None:
        """Best-effort cancellation of collection and media synchronization."""
        for abort in (self.col.abort_sync, self.col.abort_media_sync):
            try:
                abort()
            except Exception:
                logger.exception("Failed to abort an Anki synchronization operation")

    def _credentials(
        self,
        username: str | None,
        password: str | None,
        endpoint: str | None,
        *,
        operation: str,
    ) -> tuple[str, str, str | None]:
        cfg = get_config()
        user = username or cfg.ANKIWEB_USER
        pass_ = password or cfg.ANKIWEB_PASS
        url = endpoint or cfg.ANKIWEB_URL
        if not user or not pass_:
            raise ValueError(
                f"ANKICONNECT_ANKIWEB_USER and ANKICONNECT_ANKIWEB_PASS required for {operation}"
            )
        return user, pass_, url

    @staticmethod
    def _report(progress: SyncProgressCallback | None, message: str) -> None:
        if progress is not None:
            progress(message)

    def _full_download(self, auth: Any, server_usn: int) -> None:
        self.col.close_for_full_sync()
        self._closed = True
        try:
            self.col.full_upload_or_download(auth=auth, server_usn=server_usn, upload=False)
            # The backend reopens the collection internally after a full
            # download, but the Python-side db handle is still None. Reattach
            # it with reopen(after_full_sync=True) instead of constructing a
            # new Collection (which would error with "Anki already open").
            self.col.reopen(after_full_sync=True)
            self._closed = False
            self._collection_generation += 1
            logger.debug(
                "Reattached Anki collection at %s after full download",
                self.collection_path,
            )
        finally:
            if self._closed:
                # Download failed; the backend collection is closed, so fall
                # back to opening a fresh handle.
                self._reopen_collection()

    @staticmethod
    def _media_counters(status: MediaSyncStatusResponse) -> tuple[str, str, str]:
        if not status.HasField("progress"):
            return "", "", ""
        return status.progress.checked, status.progress.added, status.progress.removed

    def _wait_for_media(
        self,
        progress: SyncProgressCallback | None = None,
        *,
        timeout: float = 300.0,
        poll_interval: float = 0.1,
    ) -> MediaSyncResult:
        """Wait for the background media sync to finish and report counters.

        Anki's sync_media() returns immediately after starting the sync; without
        waiting we falsely report completion. Poll media_sync_status() until it
        reports inactive, relaying progress counters to the callback.
        """
        self._report(progress, "Synchronizing media")
        deadline = time.monotonic() + timeout
        latest: tuple[str, str, str] | None = None
        while True:
            try:
                status = self.col.media_sync_status()
            except Exception as e:
                logger.warning(f"media_sync_status poll failed: {type(e).__name__}: {e}")
                return MediaSyncResult()
            counters = self._media_counters(status)
            if counters != latest and any(counters):
                checked, added, removed = counters
                self._report(
                    progress,
                    f"Media progress: checked {checked or '0'}, "
                    f"added {added or '0'}, removed {removed or '0'}",
                )
                latest = counters
            if not status.active:
                return MediaSyncResult(
                    checked=counters[0] or None,
                    added=counters[1] or None,
                    removed=counters[2] or None,
                )
            if time.monotonic() >= deadline:
                self.abort_sync()
                raise SyncError(f"media sync timed out after {timeout}s")
            time.sleep(poll_interval)

    def sync_to_ankiweb(
        self,
        username: str | None = None,
        password: str | None = None,
        endpoint: str | None = None,
        *,
        progress: SyncProgressCallback | None = None,
    ) -> SyncResult:
        if not self._sync_lock.acquire(blocking=False):
            raise SyncError("A synchronization is already in progress")
        try:
            user, pass_, url = self._credentials(username, password, endpoint, operation="sync")
            self._report(progress, "Authenticating with AnkiWeb")
            try:
                auth = self.col.sync_login(username=user, password=pass_, endpoint=url)
            except Exception as error:
                raise SyncError(f"AnkiWeb authentication failed: {error}") from error

            self._report(progress, "Synchronizing collection")
            try:
                result = self.col.sync_collection(auth, sync_media=True)
            except Exception as error:
                self.close()
                self._reopen_collection()
                raise SyncError(f"Collection synchronization failed: {error}") from error

            # Honor a sync endpoint redirect before any full download.
            if result.new_endpoint:
                auth.endpoint = result.new_endpoint

            needs_reopen = False
            if result.required in (
                SyncCollectionResponse.FULL_SYNC,
                SyncCollectionResponse.FULL_DOWNLOAD,
            ):
                reason = (
                    DownloadReason.CONFLICT
                    if result.required == SyncCollectionResponse.FULL_SYNC
                    else DownloadReason.REMOTE_ONLY
                )
                self._report(
                    progress,
                    "Downloading the AnkiWeb collection to resolve a conflict"
                    if reason is DownloadReason.CONFLICT
                    else "Downloading the AnkiWeb collection",
                )
                try:
                    self._full_download(auth, result.server_media_usn)
                except Exception as error:
                    raise SyncError(f"Full collection download failed: {error}") from error
                collection = CollectionSyncResult(
                    outcome=CollectionSyncOutcome.DOWNLOADED,
                    download_reason=reason,
                    local_data_replaced=True,
                )
            elif result.required == SyncCollectionResponse.FULL_UPLOAD:
                # Full uploads are disabled by policy: the AnkiWeb collection is
                # empty and only a full upload would populate it, which would
                # destroy any remote data the user has. Preserve the local
                # collection and surface a clear error so the user can decide.
                raise SyncError(
                    "AnkiWeb collection is empty and only a full upload is possible; "
                    "full uploads are disabled by policy and the local collection "
                    "was preserved"
                )
            elif result.required == SyncCollectionResponse.NORMAL_SYNC:
                collection = CollectionSyncResult(
                    outcome=CollectionSyncOutcome.MERGED,
                    local_data_replaced=False,
                )
                needs_reopen = True
            elif result.required == SyncCollectionResponse.NO_CHANGES:
                collection = CollectionSyncResult(
                    outcome=CollectionSyncOutcome.NO_CHANGES,
                    local_data_replaced=False,
                )
                needs_reopen = True
            else:
                raise SyncError(f"Unsupported synchronization requirement: {result.required}")

            try:
                media = self._wait_for_media(progress)
            except Exception as error:
                raise SyncError(
                    "Media synchronization failed after collection synchronization "
                    f"completed; media remains incomplete: {error}"
                ) from error
            finally:
                if needs_reopen:
                    self.close()
                    self._reopen_collection()

            self._report(progress, "Synchronization completed")
            logger.info(
                "Sync completed: collection=%s, media=%s",
                collection.outcome,
                media.outcome,
            )
            return SyncResult(
                collection=collection,
                media=media,
                server_message=result.server_message or None,
            )
        except Exception:
            logger.exception("AnkiWeb sync failed")
            if self._closed:
                self._reopen_collection()
            raise
        finally:
            self._sync_lock.release()

    def deck_names(self) -> list[str]:
        decks = self.col.decks.all_names_and_ids()
        return [d.name for d in decks]

    def deck_names_and_ids(self) -> dict[str, int]:
        decks = self.col.decks.all_names_and_ids()
        return {d.name: int(d.id) for d in decks}

    def create_deck(self, deck: str) -> int:
        return int(cast(int, self.col.decks.id(deck)))

    def delete_decks(self, decks: list[str], cards_too: bool = False) -> None:
        for deck in decks:
            deck_id = self.col.decks.id_for_name(deck)
            if deck_id:
                if cards_too:
                    card_ids = self.col.find_cards(f"deck:{deck}")
                    if card_ids:
                        note_ids = [NoteId(n) for n in self.cards_to_notes(list(card_ids))]
                        self.col.remove_notes(note_ids)
                self.col.decks.remove([deck_id])

    def get_decks(self, cards: list[int]) -> dict[str, list[int]]:
        result: dict[str, list[int]] = {}
        for card_id in cards:
            card = self.col.get_card(CardId(card_id))
            if card:
                deck_name = self.col.decks.name(card.did)
                if deck_name not in result:
                    result[deck_name] = []
                result[deck_name].append(card_id)
        return result

    def change_deck(self, cards: list[int], deck: str) -> None:
        deck_id = cast(DeckId, self.col.decks.id(deck))
        self.col.set_deck([CardId(c) for c in cards], deck_id)

    def get_deck_config(self, deck: str) -> JsonObject:
        deck_id = self.col.decks.id_for_name(deck)
        if not deck_id:
            return {}
        return cast(JsonObject, self.col.decks.config_dict_for_deck_id(deck_id))

    def save_deck_config(self, config: JsonObject) -> bool:
        self.col.decks.update_config(cast(DeckConfigDict, config))
        return True

    def set_deck_config_id(self, decks: list[str], config_id: int) -> bool:
        for deck in decks:
            deck_id = self.col.decks.id_for_name(deck)
            if deck_id:
                deck_dict = self.col.decks.get(deck_id)
                if deck_dict is not None:
                    self.col.decks.set_config_id_for_deck_dict(deck_dict, DeckConfigId(config_id))
        return True

    def clone_deck_config_id(self, name: str, clone_from: int) -> int:
        return int(
            self.col.decks.add_config_returning_id(name, cast(DeckConfigDict | None, clone_from))
        )

    def remove_deck_config_id(self, config_id: int) -> bool:
        self.col.decks.remove_config(DeckConfigId(config_id))
        return True

    def model_names(self) -> list[str]:
        models = self.col.models.all_names_and_ids()
        return [m.name for m in models]

    def model_names_and_ids(self) -> dict[str, int]:
        models = self.col.models.all_names_and_ids()
        return {m.name: int(m.id) for m in models}

    def _get_model_by_name(self, model_name: str) -> NotetypeDict | None:
        """Get model dict by name."""
        models = self.col.models.all_names_and_ids()
        for m in models:
            if m.name == model_name:
                return self.col.models.get(NotetypeId(m.id))
        return None

    def _model_fields(self, model: NotetypeDict) -> list[FieldDict]:
        return cast(list[FieldDict], model.get("flds", []))

    def _model_templates(self, model: NotetypeDict) -> list[TemplateDict]:
        return cast(list[TemplateDict], model.get("tmpls", []))

    def model_field_names(self, model_name: str) -> list[str]:
        model = self._get_model_by_name(model_name)
        if not model:
            return []
        return [cast(str, f["name"]) for f in self._model_fields(model)]

    def model_fields_on_templates(self, model_name: str) -> dict[str, list[list[str]]]:
        model = self._get_model_by_name(model_name)
        if not model:
            return {}
        result: dict[str, list[list[str]]] = {}
        for tmpl in self._model_templates(model):
            name = cast(str, tmpl.get("name", ""))
            qfmt = cast(str, tmpl.get("qfmt", ""))
            afmt = cast(str, tmpl.get("afmt", ""))
            q_fields = self._extract_fields_from_template(qfmt)
            a_fields = self._extract_fields_from_template(afmt)
            result[name] = [q_fields, a_fields]
        return result

    def _extract_fields_from_template(self, template: str) -> list[str]:
        fields = re.findall(r"\{\{([^}]+)\}\}", template)
        return [f for f in fields if not f.startswith("!")]

    def _require_model(self, model_name: str) -> NotetypeDict:
        """Get model dict by name, raising ValueError if it doesn't exist."""
        model = self._get_model_by_name(model_name)
        if not model:
            raise ValueError(f"Model not found: {model_name}")
        return model

    def _require_field(self, model: NotetypeDict, field_name: str) -> FieldDict:
        field_map = self.col.models.field_map(model)
        if field_name not in field_map:
            raise ValueError(f"Field not found: {field_name}")
        return field_map[field_name][1]

    def model_add_field(self, model_name: str, field_name: str, index: int | None = None) -> None:
        model = self._require_model(model_name)
        if not field_name or field_name in self.col.models.field_map(model):
            raise ValueError(f"Field already exists or is empty: {field_name!r}")
        field = self.col.models.new_field(field_name)
        self.col.models.add_field(model, field)
        if index is not None:
            field_dict = self._require_field(model, field_name)
            self.col.models.reposition_field(model, field_dict, index)
        self.col.models.update(model)

    def model_remove_field(self, model_name: str, field_name: str) -> None:
        model = self._require_model(model_name)
        field = self._require_field(model, field_name)
        self.col.models.remove_field(model, field)
        self.col.models.update(model)

    def model_rename_field(self, model_name: str, old_name: str, new_name: str) -> None:
        model = self._require_model(model_name)
        field = self._require_field(model, old_name)
        self.col.models.rename_field(model, field, new_name)
        self.col.models.update(model)

    def model_reposition_field(self, model_name: str, field_name: str, index: int) -> None:
        model = self._require_model(model_name)
        field = self._require_field(model, field_name)
        self.col.models.reposition_field(model, field, index)
        self.col.models.update(model)

    def create_model(
        self,
        model_name: str,
        in_order_fields: list[str],
        card_templates: list[dict[str, str]],
        css: str = "",
        is_cloze: bool = False,
    ) -> None:
        notetype = self.col.models.new(model_name)
        for field_name in in_order_fields:
            field = self.col.models.new_field(field_name)
            self.col.models.add_field(notetype, field)

        for i, tmpl in enumerate(card_templates):
            template = self.col.models.new_template(tmpl.get("Name", f"Card {i + 1}"))
            template["qfmt"] = tmpl.get("Front", "")
            template["afmt"] = tmpl.get("Back", "")
            self.col.models.add_template(notetype, template)

        if css:
            notetype["css"] = css

        self.col.models.add(notetype)

    def model_templates(self, model_name: str) -> dict[str, dict[str, str]]:
        model = self._get_model_by_name(model_name)
        if not model:
            return {}
        result: dict[str, dict[str, str]] = {}
        for tmpl in self._model_templates(model):
            name = cast(str, tmpl.get("name", ""))
            result[name] = {
                "Front": cast(str, tmpl.get("qfmt", "")),
                "Back": cast(str, tmpl.get("afmt", "")),
            }
        return result

    def model_styling(self, model_name: str) -> JsonObject:
        model = self._get_model_by_name(model_name)
        if not model:
            return {}
        return {"css": cast(str, model.get("css", ""))}

    def update_model_templates(self, model: JsonObject) -> None:
        name = model.get("name")
        if not isinstance(name, str):
            return
        notetype = self._get_model_by_name(name)
        if not notetype:
            return
        templates = model.get("templates", {})
        if isinstance(templates, dict):
            for templates_update in templates.values():
                if not isinstance(templates_update, dict):
                    continue
                for tmpl in self._model_templates(notetype):
                    if "Front" in templates_update:
                        tmpl["qfmt"] = cast(str, templates_update["Front"])
                    if "Back" in templates_update:
                        tmpl["afmt"] = cast(str, templates_update["Back"])
        self.col.models.update(notetype)

    def update_model_styling(self, model: JsonObject) -> None:
        name = model.get("name")
        if not isinstance(name, str):
            return
        notetype = self._get_model_by_name(name)
        if not notetype:
            return
        if "css" in model:
            notetype["css"] = cast(str, model["css"])
        self.col.models.update(notetype)

    def add_note(self, note: JsonObject) -> int | None:
        model_name = note.get("modelName", "")
        if not isinstance(model_name, str):
            return None
        notetype = self._get_model_by_name(model_name)
        if not notetype:
            return None
        deck_name = note.get("deckName", "Default")
        if not isinstance(deck_name, str):
            deck_name = "Default"
        deck_id = cast(DeckId, self.col.decks.id(deck_name))
        new_note = Note(self.col, notetype)
        fields = note.get("fields", {})
        if isinstance(fields, dict):
            for field_name, value in fields.items():
                new_note[field_name] = str(value) if value is not None else ""
        tags = note.get("tags")
        if isinstance(tags, list):
            new_note.tags = [str(t) for t in tags]
        self.col.add_note(new_note, deck_id)
        return int(new_note.id)

    def add_notes(self, notes: list[JsonObject]) -> list[int | None]:
        return [self.add_note(note) for note in notes]

    def can_add_notes(self, notes: list[JsonObject]) -> list[bool]:
        return [
            bool(item.get("canAdd", False))
            for item in self.can_add_notes_with_error_detail(notes)
        ]

    def can_add_notes_with_error_detail(
        self, notes: list[JsonObject]
    ) -> list[JsonObject]:
        return [self.can_add_note_with_error_detail(note) for note in notes]

    def can_add_note_with_error_detail(self, note: JsonObject) -> JsonObject:
        try:
            self._create_note_for_validation(note)
            return {"canAdd": True}
        except Exception as e:
            return {"canAdd": False, "error": str(e)}

    def _create_note_for_validation(self, note: JsonObject) -> Note:
        model_name = note.get("modelName")
        if not model_name or not isinstance(model_name, str):
            raise Exception(f"model was not found: {model_name}")
        notetype = self._get_model_by_name(model_name)
        if not notetype:
            raise Exception(f"model was not found: {model_name}")

        deck_name = note.get("deckName")
        if not deck_name or not isinstance(deck_name, str):
            raise Exception(f"deck was not found: {deck_name}")
        deck = self.col.decks.by_name(deck_name)
        if not deck:
            raise Exception(f"deck was not found: {deck_name}")

        anki_note = Note(self.col, notetype)
        nt = anki_note.note_type()
        if nt is not None:
            nt["did"] = deck["id"]
        tags = note.get("tags")
        if isinstance(tags, list):
            anki_note.tags = [str(t) for t in tags]

        fields = note.get("fields", {})
        if isinstance(fields, dict):
            anki_keys = list(anki_note.keys())
            anki_keys_lower = {k.lower(): k for k in anki_keys}
            for name, value in fields.items():
                target_key = anki_keys_lower.get(name.lower(), name)
                if target_key in anki_note:
                    anki_note[target_key] = str(value) if value is not None else ""

        allow_duplicate = False
        duplicate_scope: str | None = None
        duplicate_scope_deck_name: str | None = None
        duplicate_scope_check_children = False
        duplicate_scope_check_all_models = False

        if "options" in note:
            options = note["options"]
            if isinstance(options, dict):
                if "allowDuplicate" in options:
                    allow_duplicate_val = options["allowDuplicate"]
                    if type(allow_duplicate_val) is not bool:
                        raise Exception('option parameter "allowDuplicate" must be boolean')
                    allow_duplicate = allow_duplicate_val
                if "duplicateScope" in options and isinstance(options["duplicateScope"], str):
                    duplicate_scope = options["duplicateScope"]
                if "duplicateScopeOptions" in options:
                    duplicate_scope_options = options["duplicateScopeOptions"]
                    if isinstance(duplicate_scope_options, dict):
                        if "deckName" in duplicate_scope_options and isinstance(
                            duplicate_scope_options["deckName"], str
                        ):
                            duplicate_scope_deck_name = duplicate_scope_options["deckName"]
                        if "checkChildren" in duplicate_scope_options:
                            check_children_val = duplicate_scope_options["checkChildren"]
                            if type(check_children_val) is not bool:
                                raise Exception(
                                    'option parameter "duplicateScopeOptions.checkChildren" must be boolean'
                                )
                            duplicate_scope_check_children = check_children_val
                        if "checkAllModels" in duplicate_scope_options:
                            check_all_models_val = duplicate_scope_options["checkAllModels"]
                            if type(check_all_models_val) is not bool:
                                raise Exception(
                                    'option parameter "duplicateScopeOptions.checkAllModels" must be boolean'
                                )
                            duplicate_scope_check_all_models = check_all_models_val

        duplicate_or_empty = self._is_note_duplicate_or_empty_in_scope(
            anki_note,
            deck,
            duplicate_scope,
            duplicate_scope_deck_name,
            duplicate_scope_check_children,
            duplicate_scope_check_all_models,
        )

        if duplicate_or_empty == 1:
            raise Exception("cannot create note because it is empty")
        if duplicate_or_empty == 2:
            if allow_duplicate:
                return anki_note
            raise Exception("cannot create note because it is a duplicate")
        if duplicate_or_empty == 0:
            return anki_note
        raise Exception("cannot create note for unknown reason")

    def _is_note_duplicate_or_empty_in_scope(
        self,
        note: Note,
        deck: dict[str, Any],
        duplicate_scope: str | None,
        duplicate_scope_deck_name: str | None,
        duplicate_scope_check_children: bool,
        duplicate_scope_check_all_models: bool,
    ) -> int:
        # Returns: 1 if first is empty, 2 if first is a duplicate, 0 otherwise.
        if duplicate_scope != "deck" and not duplicate_scope_check_all_models:
            return note.dupeOrEmpty() or 0

        # Primary field for uniqueness
        if not note.fields:
            return 1
        val = note.fields[0]
        if not val.strip():
            return 1

        stripped = self.col._backend.strip_html(  # pyright: ignore[reportPrivateUsage]
            text=val, mode=StripHtmlMode.PRESERVE_MEDIA_FILENAMES
        )
        csum = int(
            hashlib.sha1(stripped.encode("utf-8"), usedforsecurity=False).hexdigest()[:8], 16
        )

        dids: dict[int, bool] | None = None
        if duplicate_scope == "deck":
            did = deck["id"]
            if duplicate_scope_deck_name is not None:
                deck2 = self.col.decks.by_name(duplicate_scope_deck_name)
                if deck2 is None:
                    return 0
                did = deck2["id"]

            dids = {did: True}
            if duplicate_scope_check_children:
                for kv in self.col.decks.children(did):
                    dids[kv[1]] = True

        query = "select id from notes where csum=?"
        query_args: list[Any] = [csum]
        if note.id:
            query += " and id!=?"
            query_args.append(note.id)
        if not duplicate_scope_check_all_models:
            query += " and mid=?"
            query_args.append(note.mid)

        db = self.col.db
        if db is None:
            return 0

        for note_id in db.list(query, *query_args):
            if dids is None:
                return 2
            for card_deck_id in db.list("select did from cards where nid=?", note_id):
                if card_deck_id in dids:
                    return 2

        return 0

    def update_note_fields(self, note: JsonObject) -> None:
        note_id = note.get("id")
        if not isinstance(note_id, int):
            raise ValueError("updateNoteFields requires an 'id' field")
        try:
            note_obj = self.col.get_note(NoteId(note_id))
        except Exception as e:
            raise ValueError(f"Note {note_id} not found: {e}") from e
        fields = note.get("fields", {})
        if isinstance(fields, dict):
            for field_name, value in fields.items():
                note_obj[field_name] = str(value) if value is not None else ""
        self.col.update_note(note_obj)

    def update_note_tags(self, note_id: int, tags: list[str]) -> None:
        """Set a note's tags, replacing any existing ones."""
        try:
            note_obj = self.col.get_note(NoteId(note_id))
        except Exception as e:
            raise ValueError(f"Note {note_id} not found: {e}") from e
        note_obj.tags = [str(t) for t in tags]
        self.col.update_note(note_obj)

    def update_note(self, note: JsonObject) -> None:
        """Update the fields and/or tags of an existing note.

        Mirrors upstream Anki-Connect updateNote: fields are applied first
        and are not rolled back if the tag update fails; a note with
        neither fields nor tags fails.
        """
        note_id = note.get("id")
        if not isinstance(note_id, int):
            raise ValueError("updateNote requires an 'id' field")
        fields = note.get("fields")
        tags = note.get("tags")
        field_map = fields if isinstance(fields, dict) else {}
        tag_list = [str(t) for t in tags] if isinstance(tags, list) else []
        if not field_map and not tag_list:
            raise ValueError("updateNote requires 'fields' and/or 'tags'")
        if field_map:
            self.update_note_fields(note)
        if tag_list:
            self.update_note_tags(note_id, tag_list)

    def add_tags(self, notes: list[int], tags: str) -> None:
        self.col.tags.bulk_add([NoteId(n) for n in notes], tags)

    def remove_tags(self, notes: list[int], tags: str) -> None:
        self.col.tags.bulk_remove([NoteId(n) for n in notes], tags)

    def get_tags(self) -> list[str]:
        return list(self.col.tags.all())

    def find_notes(self, query: str) -> list[int]:
        return [int(n) for n in self.col.find_notes(query)]

    def notes_info(self, notes: list[int]) -> list[JsonObject]:
        result: list[JsonObject] = []
        for note_id in notes:
            try:
                note = self.col.get_note(NoteId(note_id))
            except Exception as e:
                logger.debug("notes_info: skipping note %s: %s", note_id, e)
                continue
            model = self.col.models.get(note.mid)
            fields: dict[str, JsonObject] = {}
            for i, (name, value) in enumerate(note.items()):
                fields[name] = {"value": value, "order": i}
            result.append(
                cast(
                    JsonObject,
                    {
                        "noteId": int(note.id),
                        "modelName": model["name"] if model else "",
                        "tags": list(note.tags),
                        "fields": fields,
                    },
                )
            )
        return result

    def delete_notes(self, notes: list[int]) -> None:
        self.col.remove_notes([NoteId(n) for n in notes])

    def find_cards(self, query: str) -> list[int]:
        return [int(c) for c in self.col.find_cards(query)]

    def cards_to_notes(self, cards: list[int]) -> list[int]:
        note_ids: set[int] = set()
        for c in cards:
            card = self.col.get_card(CardId(c))
            if card:
                note_ids.add(int(card.nid))
        return list(note_ids)

    def cards_info(self, cards: list[int]) -> list[JsonObject]:
        result: list[JsonObject] = []
        for card_id in cards:
            try:
                card = self.col.get_card(CardId(card_id))
            except Exception as e:
                logger.debug("cards_info: skipping card %s: %s", card_id, e)
                continue
            note = card.note()
            model = self.col.models.get(note.mid)
            fields: dict[str, JsonObject] = {}
            for i, (name, value) in enumerate(note.items()):
                fields[name] = {"value": value, "order": i}
            result.append(
                cast(
                    JsonObject,
                    {
                        "cardId": int(card.id),
                        "note": int(note.id),
                        "deckName": self.col.decks.name(card.did),
                        "modelName": model["name"] if model else "",
                        "fields": fields,
                        "interval": card.ivl,
                        "ease": card.factor,
                        "question": card.q(reload=True),  # type: ignore[union-attr]
                        "answer": card.a(),  # type: ignore[union-attr]
                    },
                )
            )
        return result

    def suspend(self, cards: list[int]) -> bool:
        card_ids = [CardId(c) for c in cards]
        if not card_ids:
            return True
        self.col.sched.suspend_cards(card_ids)
        return True

    def unsuspend(self, cards: list[int]) -> bool:
        card_ids = [CardId(c) for c in cards]
        self.col.sched.unsuspend_cards(card_ids)
        return True

    def are_suspended(self, cards: list[int]) -> list[bool]:
        result: list[bool] = []
        for c in cards:
            try:
                card = self.col.get_card(CardId(c))
            except Exception:
                result.append(False)
                continue
            result.append(card.queue == -1)
        return result

    def are_due(self, cards: list[int]) -> list[bool]:
        result: list[bool] = []
        for c in cards:
            try:
                card = self.col.get_card(CardId(c))
            except Exception:
                result.append(False)
                continue
            if card.queue in (1, 3):
                result.append(True)
            elif card.queue == 2:
                result.append(card.due <= 0)
            else:
                result.append(False)
        return result

    def get_intervals(self, cards: list[int], complete: bool = False) -> list[Any]:
        result: list[Any] = []
        for card_id in cards:
            try:
                card = self.col.get_card(CardId(card_id))
            except Exception:
                result.append(None)
                continue
            if complete:
                last_interval = self._last_interval_from_revlog(card_id)
                result.append(
                    cast(
                        JsonObject,
                        {
                            "interval": card.ivl,
                            # last_interval is the previous interval in days, sourced
                            # from the most recent review log entry. Falls back to the
                            # current interval when there is no review history (e.g.
                            # a brand-new card).
                            "last_interval": last_interval
                            if last_interval is not None
                            else card.ivl,
                            "is_learning": card.queue in (1, 3),
                            "is_mature": card.ivl >= 21,
                        },
                    )
                )
            else:
                result.append(card.ivl)
        return result

    def _last_interval_from_revlog(self, card_id: int) -> int | None:
        """Return the previous interval (days) from the review log, or None
        if there is no review history.

        Anki's revlog entries record the interval *resulting* from each
        review. The 'previous interval' is therefore the interval of the
        second-to-most-recent entry (the most recent entry's interval is
        the current interval). For a single review, there is no previous
        interval and we return 0 (matching the AnkiConnect convention).
        """
        try:
            stats = self.col.card_stats_data(CardId(card_id))
        except Exception:
            return None
        entries = list(stats.revlog)
        if not entries:
            return None
        if len(entries) == 1:
            return 0
        previous = entries[-2]
        return int(previous.interval)

    def get_media_dir_path(self) -> str:
        return self.col.media.dir()

    def store_media_file(self, filename: str, data: str, url: str = "", path: str = "") -> None:
        """Store media from base64 data, a URL, or a server-side file path.

        Mirrors upstream Anki-Connect: exactly one source must be provided,
        with data taking precedence over url and path.
        """
        if data:
            file_data = base64.b64decode(data)
        elif url:
            file_data = self._download_media(url)
        elif path:
            try:
                file_data = Path(path).read_bytes()
            except OSError as error:
                raise ValueError(f"Cannot read media file at {path}: {error}") from error
        else:
            raise ValueError("One of data, url or path is required")
        self.col.media.write_data(filename, file_data)

    @staticmethod
    def _download_media(url: str) -> bytes:
        """Download media from url, following redirects."""
        try:
            with Client(follow_redirects=True, timeout=30) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.content
        except HTTPError as error:
            raise ValueError(f"Cannot download media from {url}: {error}") from error

    def _sanitize_media_filename(self, filename: str) -> str:
        """Normalize a media filename the same way Anki-Connect does.

        basename() blocks traversal, NFC avoids duplicate files from
        decomposed Unicode, and illegal chars are stripped (mirrors
        MediaManager._legacy_strip_illegal, kept by anki for AnkiConnect).
        """
        filename = Path(filename).name
        if filename in (".", ".."):
            return ""
        filename = unicodedata.normalize("NFC", filename)
        return re.sub(r'[][><:"/?*^\\|\0\r\n]', "", filename)

    def retrieve_media_file(self, filename: str) -> str | None:
        """Read a media file and return it base64-encoded, or None if missing.

        MediaManager has no read API (anki 26.x); the file lives directly in
        the media dir, so read it from disk after basename/NFC/illegal-char
        sanitization, matching upstream Anki-Connect.
        """
        filename = self._sanitize_media_filename(filename)
        if not filename:
            return None
        try:
            if not self.col.media.have(filename):
                return None
            path = Path(self.col.media.dir()) / filename
            return base64.b64encode(path.read_bytes()).decode()
        except OSError:
            return None

    def delete_media_file(self, filename: str) -> None:
        self.col.media.trash_files([self._sanitize_media_filename(filename)])

    def import_package(self, path: str) -> JsonObject:
        return cast(JsonObject, self.col.import_anki_package(path))  # type: ignore[call-arg]

    def export_package(self, deck: str, path: str, include_sched: bool = False) -> None:
        deck_id = cast(DeckId, self.col.decks.id(deck))
        self.col.export_anki_package(path, deck_id, include_sched)  # type: ignore[call-arg]

    def sync_status(
        self,
        username: str | None = None,
        password: str | None = None,
        endpoint: str | None = None,
    ) -> JsonObject:
        cfg = get_config()
        user = username or cfg.ANKIWEB_USER
        pass_ = password or cfg.ANKIWEB_PASS
        url = endpoint or cfg.ANKIWEB_URL

        if not user or not pass_:
            raise ValueError(
                "ANKICONNECT_ANKIWEB_USER and ANKICONNECT_ANKIWEB_PASS required for sync status"
            )

        auth = self.col.sync_login(
            username=user,
            password=pass_,
            endpoint=url,
        )
        status = self.col.sync_status(auth)
        return {
            "server": getattr(status, "server", str(status)),
            "status": getattr(status, "status", str(status)),
            "required": getattr(status, "required", 0),
        }

    def sync_media_only(
        self,
        username: str | None = None,
        password: str | None = None,
        endpoint: str | None = None,
        *,
        progress: SyncProgressCallback | None = None,
        timeout: float = 300.0,
        poll_interval: float = 0.1,
    ) -> MediaSyncResult:
        """Run only the media sync (not the collection) and wait for completion."""
        user, pass_, url = self._credentials(username, password, endpoint, operation="media sync")

        if not self._sync_lock.acquire(blocking=False):
            raise SyncError("A synchronization is already in progress")
        try:
            auth = self.col.sync_login(username=user, password=pass_, endpoint=url)
            self.col.sync_media(auth)
            return self._wait_for_media(progress, timeout=timeout, poll_interval=poll_interval)
        finally:
            self._sync_lock.release()
