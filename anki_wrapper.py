import os
import base64
import logging
from pathlib import Path
from typing import Any, Optional

from anki.collection import Collection
from anki.cards import CardId
from anki.decks import DeckId
from anki.notes import Note, NoteId
from anki.models import NotetypeDict

from config import config

logger = logging.getLogger(__name__)


class AnkiWrapper:
    def __init__(self, collection_path: str):
        Collection.initialize_backend_logging()
        self.collection_path = collection_path
        self.col = Collection(collection_path)

    def close(self):
        if self.col:
            self.col.close()

    def sync_to_ankiweb(self) -> str:
        if not config.ANKIWEB_USER or not config.ANKIWEB_PASS:
            raise ValueError("ANKICONNECT_ANKIWEB_USER and ANKIWEB_PASS required for sync")

        endpoint = config.ANKIWEB_URL
        auth = self.col.sync_login(
            username=config.ANKIWEB_USER,
            password=config.ANKIWEB_PASS,
            endpoint=endpoint,
        )
        
        result = self.col.sync_collection(auth, sync_media=False)
        
        try:
            if result.required == 3:
                self.col.close_for_full_sync()
                self.col.full_upload_or_download(
                    auth=auth, server_usn=result.server_media_usn, upload=False
                )
                self.col = Collection(self.collection_path)
            elif result.required == 4:
                self.col.close_for_full_sync()
                self.col.full_upload_or_download(
                    auth=auth, server_usn=result.server_media_usn, upload=True
                )
                self.col = Collection(self.collection_path)
            else:
                self.col.close()
                self.col = Collection(self.collection_path)
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.col = Collection(self.collection_path)
            raise
        
        logger.info(f"Sync completed: host={result.host_number}, required={result.required}")
        return f"sync completed: host={result.host_number}, required={result.required}"

    def deck_names(self) -> list[str]:
        decks = self.col.decks.all_names_and_ids()
        return [d.name for d in decks]

    def deck_names_and_ids(self) -> dict[str, int]:
        decks = self.col.decks.all_names_and_ids()
        return {d.name: d.id for d in decks}

    def create_deck(self, deck: str) -> int:
        return self.col.decks.id(deck)

    def delete_decks(self, decks: list[str], cards_too: bool = False) -> None:
        for deck in decks:
            deck_id = self.col.decks.id_for_name(deck)
            if deck_id:
                if cards_too:
                    card_ids = self.col.find_cards(f"deck:{deck}")
                    if card_ids:
                        self.col.remove_notes(list(self.cards_to_notes(card_ids)))
                self.col.decks.remove([deck_id])

    def get_decks(self, cards: list[int]) -> dict[str, list[int]]:
        result = {}
        for card_id in cards:
            card = self.col.get_card(CardId(card_id))
            if card:
                deck_name = self.col.decks.name(card.did)
                if deck_name not in result:
                    result[deck_name] = []
                result[deck_name].append(card_id)
        return result

    def change_deck(self, cards: list[int], deck: str) -> None:
        deck_id = self.col.decks.id(deck)
        self.col.set_deck([CardId(c) for c in cards], deck_id)

    def get_deck_config(self, deck: str) -> dict:
        config_id = self.col.decks.config_id_for_deck(deck)
        return self.col.decks.get_config(config_id)

    def save_deck_config(self, config: dict) -> bool:
        self.col.decks.save_config(config)
        return True

    def set_deck_config_id(self, decks: list[str], config_id: int) -> bool:
        for deck in decks:
            deck_id = self.col.decks.id(deck)
            self.col.decks.set_config_id_for_deck(deck_id, config_id)
        return True

    def clone_deck_config_id(self, name: str, clone_from: int) -> int:
        return self.col.decks.clone_config_id(name, clone_from)

    def remove_deck_config_id(self, config_id: int) -> bool:
        self.col.decks.remove_config(config_id)
        return True

    def model_names(self) -> list[str]:
        models = self.col.models.all_names_and_ids()
        return [m.name for m in models]

    def model_names_and_ids(self) -> dict[str, int]:
        models = self.col.models.all_names_and_ids()
        return {m.name: m.id for m in models}

    def _get_model_by_name(self, model_name: str):
        """Get model dict by name."""
        models = self.col.models.all_names_and_ids()
        for m in models:
            if m.name == model_name:
                return self.col.models.get(m.id)
        return None

    def model_field_names(self, model_name: str) -> list[str]:
        model = self._get_model_by_name(model_name)
        if not model:
            return []
        return [f["name"] for f in model.get("flds", [])]

    def model_fields_on_templates(self, model_name: str) -> dict[str, list[list[str]]]:
        model = self._get_model_by_name(model_name)
        if not model:
            return {}
        result = {}
        for name, tmpl in model["tmpls"].items():
            qfmt = [f["name"] for f in tmpl.get("qfmt", [])]
            afmt = [f["name"] for f in tmpl.get("afmt", [])]
            result[name] = [qfmt, afmt]
        return result

    def create_model(
        self,
        model_name: str,
        in_order_fields: list[str],
        card_templates: list[dict],
        css: str = "",
        is_cloze: bool = False,
    ) -> None:
        notetype = self.col.models.new_note_type(model_name)
        for i, field_name in enumerate(in_order_fields):
            field = self.col.models.new_field(field_name)
            self.col.models.add_field(notetype, field)

        for i, tmpl in enumerate(card_templates):
            template = self.col.models.new_template(tmpl.get("Name", f"Card {i+1}"))
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
        result = {}
        for name, tmpl in model["tmpls"].items():
            result[name] = {"Front": tmpl.get("qfmt", ""), "Back": tmpl.get("afmt", "")}
        return result

    def model_styling(self, model_name: str) -> dict[str, Any]:
        model = self._get_model_by_name(model_name)
        if not model:
            return {}
        return {"css": model.get("css", "")}

    def update_model_templates(self, model: dict) -> None:
        notetype = self._get_model_by_name(model["name"])
        if not notetype:
            return
        for name, templates in model.get("templates", {}).items():
            if name in notetype["tmpls"]:
                if "Front" in templates:
                    notetype["tmpls"][name]["qfmt"] = templates["Front"]
                if "Back" in templates:
                    notetype["tmpls"][name]["afmt"] = templates["Back"]
        self.col.models.update_notetype(notetype)

    def update_model_styling(self, model: dict) -> None:
        notetype = self._get_model_by_name(model["name"])
        if not notetype:
            return
        if "css" in model:
            notetype["css"] = model["css"]
        self.col.models.update_notetype(notetype)

    def add_note(self, note: dict) -> Optional[int]:
        model_name = note.get("modelName", "")
        notetype = self._get_model_by_name(model_name)
        if not notetype:
            return None
        deck_id = self.col.decks.id(note.get("deckName", "Default"))
        new_note = Note(self.col, notetype)
        for field_name, value in note.get("fields", {}).items():
            new_note[field_name] = value
        if "tags" in note:
            new_note.tags = note["tags"]
        self.col.add_note(new_note, deck_id)
        return new_note.id

    def add_notes(self, notes: list[dict]) -> list[Optional[int]]:
        results = []
        for note in notes:
            results.append(self.add_note(note))
        return results

    def can_add_notes(self, notes: list[dict]) -> list[bool]:
        return [bool(self.add_note(n)) for n in notes]

    def update_note_fields(self, note: dict) -> None:
        note_id = note.get("id")
        if not note_id:
            return
        note_obj = self.col.get_note(NoteId(note_id))
        if not note_obj:
            return
        for field_name, value in note.get("fields", {}).items():
            note_obj[field_name] = value
        self.col.update_note(note_obj)

    def add_tags(self, notes: list[int], tags: str) -> None:
        self.col.tags.add_tags((NoteId(n) for n in notes), tags.split())

    def remove_tags(self, notes: list[int], tags: str) -> None:
        self.col.tags.remove_tags((NoteId(n) for n in notes), tags.split())

    def get_tags(self) -> list[str]:
        return list(self.col.tags.all())

    def find_notes(self, query: str) -> list[int]:
        return list(self.col.find_notes(query))

    def notes_info(self, notes: list[int]) -> list[dict]:
        result = []
        for note_id in notes:
            note = self.col.get_note(NoteId(note_id))
            if not note:
                continue
            model = self.col.models.get(note.mid)
            result.append({
                "noteId": note.id,
                "modelName": model["name"] if model else "",
                "tags": list(note.tags),
                "fields": {
                    name: {"value": value, "order": i}
                    for i, (name, value) in enumerate(note.items())
                },
            })
        return result

    def delete_notes(self, notes: list[int]) -> None:
        self.col.remove_notes(NoteId(n) for n in notes)

    def find_cards(self, query: str) -> list[int]:
        return list(self.col.find_cards(query))

    def cards_to_notes(self, cards: list[int]) -> list[int]:
        note_ids = []
        for c in cards:
            card = self.col.get_card(CardId(c))
            if card:
                note_ids.append(card.nid)
        return list(set(note_ids))

    def cards_info(self, cards: list[int]) -> list[dict]:
        result = []
        for card_id in cards:
            card = self.col.get_card(CardId(card_id))
            if not card:
                continue
            note = card.note()
            model = self.col.models.get(note.mid)
            result.append({
                "cardId": card.id,
                "note": note.id,
                "deckName": self.col.decks.name(card.did),
                "modelName": model["name"] if model else "",
                "fields": {
                    name: {"value": value, "order": i}
                    for i, (name, value) in enumerate(note.items())
                },
                "interval": card.ivl,
                "ease": card.factor,
                "question": card.q(reload=True),
                "answer": card.a(),
            })
        return result

    def suspend(self, cards: list[int]) -> bool:
        card_ids = [CardId(c) for c in cards]
        suspended = self.col.sched.suspend_cards(card_ids)
        return suspended.count > 0 if hasattr(suspended, 'count') else True

    def unsuspend(self, cards: list[int]) -> bool:
        card_ids = [CardId(c) for c in cards]
        self.col.sched.unsuspend_cards(card_ids)
        return True

    def are_suspended(self, cards: list[int]) -> list[bool]:
        return [self.col.get_card(CardId(c)).queue == -1 for c in cards]

    def are_due(self, cards: list[int]) -> list[bool]:
        result = []
        for c in cards:
            card = self.col.get_card(CardId(c))
            if card.queue in (1, 3):
                result.append(True)
            elif card.queue == 2:
                result.append(card.due <= 0)
            else:
                result.append(False)
        return result

    def get_intervals(self, cards: list[int], complete: bool = False) -> list[Any]:
        result = []
        for card_id in cards:
            card = self.col.get_card(CardId(card_id))
            if not card:
                result.append(None)
                continue
            if complete:
                result.append({
                    "interval": card.ivl,
                    "last_interval": getattr(card, 'lapses', 0),
                    "is_learning": card.queue in (1, 3),
                    "is_mature": card.ivl >= 21,
                })
            else:
                result.append(card.ivl)
        return result

    def get_media_dir_path(self) -> str:
        return self.col.media.dir()

    def store_media_file(self, filename: str, data: str) -> None:
        file_data = base64.b64decode(data)
        self.col.media.write_data(filename, file_data)

    def retrieve_media_file(self, filename: str) -> Optional[str]:
        try:
            data = self.col.media.read_data(filename)
            return base64.b64encode(data).decode()
        except Exception:
            return None

    def delete_media_file(self, filename: str) -> None:
        self.col.media.delete_file(filename)

    def import_package(self, path: str) -> dict:
        return self.col.import_anki_package(path)

    def export_package(self, deck: str, path: str, include_sched: bool = False) -> None:
        deck_id = self.col.decks.id(deck)
        self.col.export_anki_package(path, deck_id, include_sched)

    def sync_status(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> dict:
        user = username or config.ANKIWEB_USER
        pass_ = password or config.ANKIWEB_PASS
        url = endpoint or config.ANKIWEB_URL

        if not user or not pass_:
            raise ValueError("ANKICONNECT_ANKIWEB_USER and ANKIWEB_PASS required for sync status")

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

    def sync_media_only(self) -> str:
        if not config.ANKIWEB_USER or not config.ANKIWEB_PASS:
            raise ValueError("ANKICONNECT_ANKIWEB_USER and ANKIWEB_PASS required for media sync")

        endpoint = config.ANKIWEB_URL
        auth = self.col.sync_login(
            username=config.ANKIWEB_USER,
            password=config.ANKIWEB_PASS,
            endpoint=endpoint,
        )
        self.col.sync_media(auth)
        logger.info("Media sync completed")
        return "media sync completed"

    def get_sync_auth(self) -> Any:
        if not config.ANKIWEB_USER or not config.ANKIWEB_PASS:
            return None
        endpoint = config.ANKIWEB_URL
        return self.col.sync_login(
            username=config.ANKIWEB_USER,
            password=config.ANKIWEB_PASS,
            endpoint=endpoint,
        )