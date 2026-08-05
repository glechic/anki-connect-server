import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from anki_connect_server.anki_wrapper import AnkiWrapper
from anki_connect_server.sync import MediaSyncResult, SyncResult
from anki_connect_server.types import (
    AddNoteParams,
    AddNotesParams,
    AddTagsParams,
    CardsIdsParams,
    ChangeDeckParams,
    CloneDeckConfigIdParams,
    CreateDeckParams,
    CreateModelParams,
    CredentialsParams,
    DeleteDecksParams,
    EmptyParams,
    ExportPackageParams,
    FilenameParams,
    FindCardsParams,
    FindNotesParams,
    GetDeckConfigParams,
    GetDecksParams,
    GetIntervalsParams,
    ImportPackageParams,
    JsonObject,
    ModelNameParams,
    ModelStylingUpdateParams,
    ModelTemplateUpdateParams,
    MultiParams,
    NotesIdsParams,
    RemoveDeckConfigIdParams,
    SaveDeckConfigParams,
    SetDeckConfigIdParams,
    StoreMediaFileParams,
    UpdateNoteFieldsParams,
)

logger = logging.getLogger(__name__)


class ActionError(ValueError):
    """Raised for client-facing action errors (unknown action, bad params)."""


# A handler takes (wrapper, validated_params) and returns a JSON-serialisable
# value or coroutine resolving to one.
type Handler[P: BaseModel] = Callable[[AnkiWrapper, P], Awaitable[Any] | Any]


async def _run[R](func: Callable[..., R], *args: object, **kwargs: object) -> R:
    """Run a blocking AnkiWrapper method in a worker thread.

    The handlers are async so they can be composed by handle_multi and tested
    with await, but the underlying AnkiWrapper methods are blocking. Running
    them in asyncio.to_thread keeps the event loop responsive during long
    collection operations (find_cards over a large collection, sync, etc.).
    """
    return await asyncio.to_thread(func, *args, **kwargs)


API_VERSION = 6


# ---------------------------------------------------------------------------
# Handlers. Each handler receives an already-validated pydantic model.
# ---------------------------------------------------------------------------


async def handle_version(wrapper: AnkiWrapper, params: EmptyParams) -> int:
    _ = (wrapper, params)
    return API_VERSION


async def handle_sync(wrapper: AnkiWrapper, params: CredentialsParams) -> SyncResult:
    return await _run(wrapper.sync_to_ankiweb, params.username, params.password, params.endpoint)


async def handle_sync_status(wrapper: AnkiWrapper, params: CredentialsParams) -> JsonObject:
    return await _run(
        wrapper.sync_status,
        username=params.username,
        password=params.password,
        endpoint=params.endpoint,
    )


async def handle_sync_media(wrapper: AnkiWrapper, params: CredentialsParams) -> MediaSyncResult:
    return await _run(wrapper.sync_media_only, params.username, params.password, params.endpoint)


async def handle_deck_names(wrapper: AnkiWrapper, params: EmptyParams) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.deck_names)


async def handle_deck_names_and_ids(wrapper: AnkiWrapper, params: EmptyParams) -> dict[str, int]:
    _ = (wrapper, params)
    return await _run(wrapper.deck_names_and_ids)


async def handle_get_decks(wrapper: AnkiWrapper, params: GetDecksParams) -> dict[str, list[int]]:
    return await _run(wrapper.get_decks, params.cards)


async def handle_create_deck(wrapper: AnkiWrapper, params: CreateDeckParams) -> int:
    if not params.deck:
        raise ActionError("Deck name cannot be empty")
    return await _run(wrapper.create_deck, params.deck)


async def handle_change_deck(wrapper: AnkiWrapper, params: ChangeDeckParams) -> None:
    await _run(wrapper.change_deck, params.cards, params.deck)


async def handle_delete_decks(wrapper: AnkiWrapper, params: DeleteDecksParams) -> None:
    await _run(wrapper.delete_decks, params.decks, params.cardsToo)


async def handle_get_deck_config(wrapper: AnkiWrapper, params: GetDeckConfigParams) -> JsonObject:
    return await _run(wrapper.get_deck_config, params.deck)


async def handle_save_deck_config(wrapper: AnkiWrapper, params: SaveDeckConfigParams) -> bool:
    return await _run(wrapper.save_deck_config, params.config)


async def handle_set_deck_config_id(wrapper: AnkiWrapper, params: SetDeckConfigIdParams) -> bool:
    return await _run(wrapper.set_deck_config_id, params.decks, params.configId)


async def handle_clone_deck_config_id(wrapper: AnkiWrapper, params: CloneDeckConfigIdParams) -> int:
    return await _run(wrapper.clone_deck_config_id, params.name, params.cloneFrom)


async def handle_remove_deck_config_id(
    wrapper: AnkiWrapper, params: RemoveDeckConfigIdParams
) -> bool:
    return await _run(wrapper.remove_deck_config_id, params.configId)


async def handle_model_names(wrapper: AnkiWrapper, params: EmptyParams) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.model_names)


async def handle_model_names_and_ids(wrapper: AnkiWrapper, params: EmptyParams) -> dict[str, int]:
    _ = (wrapper, params)
    return await _run(wrapper.model_names_and_ids)


async def handle_model_field_names(wrapper: AnkiWrapper, params: ModelNameParams) -> list[str]:
    return await _run(wrapper.model_field_names, params.modelName)


async def handle_model_fields_on_templates(wrapper: AnkiWrapper, params: ModelNameParams) -> Any:
    return await _run(wrapper.model_fields_on_templates, params.modelName)


async def handle_create_model(wrapper: AnkiWrapper, params: CreateModelParams) -> None:
    await _run(
        wrapper.create_model,
        params.modelName,
        params.inOrderFields,
        params.cardTemplates,
        params.css,
        params.isCloze,
    )


async def handle_model_templates(wrapper: AnkiWrapper, params: ModelNameParams) -> Any:
    return await _run(wrapper.model_templates, params.modelName)


async def handle_model_styling(wrapper: AnkiWrapper, params: ModelNameParams) -> JsonObject:
    return await _run(wrapper.model_styling, params.modelName)


async def handle_update_model_templates(
    wrapper: AnkiWrapper, params: ModelTemplateUpdateParams
) -> None:
    await _run(wrapper.update_model_templates, params.model)


async def handle_update_model_styling(
    wrapper: AnkiWrapper, params: ModelStylingUpdateParams
) -> None:
    await _run(wrapper.update_model_styling, params.model)


async def handle_add_note(wrapper: AnkiWrapper, params: AddNoteParams) -> int | None:
    return await _run(wrapper.add_note, params.note)


async def handle_add_notes(wrapper: AnkiWrapper, params: AddNotesParams) -> list[int | None]:
    return await _run(wrapper.add_notes, params.notes)


async def handle_can_add_notes(wrapper: AnkiWrapper, params: AddNotesParams) -> list[bool]:
    return await _run(wrapper.can_add_notes, params.notes)


async def handle_update_note_fields(wrapper: AnkiWrapper, params: UpdateNoteFieldsParams) -> None:
    await _run(wrapper.update_note_fields, params.note.model_dump())


async def handle_add_tags(wrapper: AnkiWrapper, params: AddTagsParams) -> None:
    await _run(wrapper.add_tags, params.notes, params.tags)


async def handle_remove_tags(wrapper: AnkiWrapper, params: AddTagsParams) -> None:
    await _run(wrapper.remove_tags, params.notes, params.tags)


async def handle_get_tags(wrapper: AnkiWrapper, params: EmptyParams) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.get_tags)


async def handle_find_notes(wrapper: AnkiWrapper, params: FindNotesParams) -> list[int]:
    return await _run(wrapper.find_notes, params.query)


async def handle_notes_info(wrapper: AnkiWrapper, params: NotesIdsParams) -> list[JsonObject]:
    return await _run(wrapper.notes_info, params.notes)


async def handle_delete_notes(wrapper: AnkiWrapper, params: NotesIdsParams) -> None:
    await _run(wrapper.delete_notes, params.notes)


async def handle_find_cards(wrapper: AnkiWrapper, params: FindCardsParams) -> list[int]:
    return await _run(wrapper.find_cards, params.query)


async def handle_cards_to_notes(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[int]:
    return await _run(wrapper.cards_to_notes, params.cards)


async def handle_cards_info(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[JsonObject]:
    return await _run(wrapper.cards_info, params.cards)


async def handle_suspend(wrapper: AnkiWrapper, params: CardsIdsParams) -> bool:
    return await _run(wrapper.suspend, params.cards)


async def handle_unsuspend(wrapper: AnkiWrapper, params: CardsIdsParams) -> bool:
    return await _run(wrapper.unsuspend, params.cards)


async def handle_are_suspended(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[bool]:
    return await _run(wrapper.are_suspended, params.cards)


async def handle_are_due(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[bool]:
    return await _run(wrapper.are_due, params.cards)


async def handle_get_intervals(wrapper: AnkiWrapper, params: GetIntervalsParams) -> list[Any]:
    return await _run(wrapper.get_intervals, params.cards, params.complete)


async def handle_get_media_dir_path(wrapper: AnkiWrapper, params: EmptyParams) -> str:
    _ = (wrapper, params)
    return await _run(wrapper.get_media_dir_path)


async def handle_store_media_file(wrapper: AnkiWrapper, params: StoreMediaFileParams) -> None:
    await _run(wrapper.store_media_file, params.filename, params.data)


async def handle_retrieve_media_file(wrapper: AnkiWrapper, params: FilenameParams) -> str | None:
    return await _run(wrapper.retrieve_media_file, params.filename)


async def handle_delete_media_file(wrapper: AnkiWrapper, params: FilenameParams) -> None:
    await _run(wrapper.delete_media_file, params.filename)


async def handle_import_package(wrapper: AnkiWrapper, params: ImportPackageParams) -> JsonObject:
    return await _run(wrapper.import_package, params.path)


async def handle_export_package(wrapper: AnkiWrapper, params: ExportPackageParams) -> None:
    await _run(wrapper.export_package, params.deck, params.path, params.includeSched)


async def handle_multi(wrapper: AnkiWrapper, params: MultiParams) -> list[Any]:
    results: list[Any] = []
    for action in params.actions:
        if not isinstance(action, dict):
            results.append(
                {"error": f"Invalid action: expected object, got {type(action).__name__}"}
            )
            continue
        action_name = action.get("action", "")
        if not isinstance(action_name, str):
            results.append({"error": "Invalid action: 'action' must be a string"})
            continue
        entry = ACTION_HANDLERS.get(action_name)
        if not entry:
            results.append({"error": f"Unknown action: {action_name}"})
            continue
        model_cls, handler = entry
        action_params = action.get("params", {})
        if not isinstance(action_params, dict):
            results.append({"error": f"Invalid params for {action_name}: expected object"})
            continue
        try:
            validated = model_cls(**action_params)
            result = handler(wrapper, validated)
            if asyncio.iscoroutine(result):
                result = await result
            results.append(result)
        except Exception as e:
            # Per-action failure does not abort the whole multi call.
            # AnkiConnect returns an error string per action.
            results.append({"error": str(e)})
    return results


# Registry mapping AnkiConnect action names to (pydantic param model, handler).
ACTION_HANDLERS: dict[str, tuple[type[BaseModel], Handler[Any]]] = {
    "version": (EmptyParams, handle_version),
    "sync": (CredentialsParams, handle_sync),
    "syncStatus": (CredentialsParams, handle_sync_status),
    "syncMedia": (CredentialsParams, handle_sync_media),
    "deckNames": (EmptyParams, handle_deck_names),
    "deckNamesAndIds": (EmptyParams, handle_deck_names_and_ids),
    "getDecks": (GetDecksParams, handle_get_decks),
    "createDeck": (CreateDeckParams, handle_create_deck),
    "changeDeck": (ChangeDeckParams, handle_change_deck),
    "deleteDecks": (DeleteDecksParams, handle_delete_decks),
    "getDeckConfig": (GetDeckConfigParams, handle_get_deck_config),
    "saveDeckConfig": (SaveDeckConfigParams, handle_save_deck_config),
    "setDeckConfigId": (SetDeckConfigIdParams, handle_set_deck_config_id),
    "cloneDeckConfigId": (CloneDeckConfigIdParams, handle_clone_deck_config_id),
    "removeDeckConfigId": (RemoveDeckConfigIdParams, handle_remove_deck_config_id),
    "modelNames": (EmptyParams, handle_model_names),
    "modelNamesAndIds": (EmptyParams, handle_model_names_and_ids),
    "modelFieldNames": (ModelNameParams, handle_model_field_names),
    "modelFieldsOnTemplates": (ModelNameParams, handle_model_fields_on_templates),
    "createModel": (CreateModelParams, handle_create_model),
    "modelTemplates": (ModelNameParams, handle_model_templates),
    "modelStyling": (ModelNameParams, handle_model_styling),
    "updateModelTemplates": (ModelTemplateUpdateParams, handle_update_model_templates),
    "updateModelStyling": (ModelStylingUpdateParams, handle_update_model_styling),
    "addNote": (AddNoteParams, handle_add_note),
    "addNotes": (AddNotesParams, handle_add_notes),
    "canAddNotes": (AddNotesParams, handle_can_add_notes),
    "updateNoteFields": (UpdateNoteFieldsParams, handle_update_note_fields),
    "addTags": (AddTagsParams, handle_add_tags),
    "removeTags": (AddTagsParams, handle_remove_tags),
    "getTags": (EmptyParams, handle_get_tags),
    "findNotes": (FindNotesParams, handle_find_notes),
    "notesInfo": (NotesIdsParams, handle_notes_info),
    "deleteNotes": (NotesIdsParams, handle_delete_notes),
    "findCards": (FindCardsParams, handle_find_cards),
    "cardsToNotes": (CardsIdsParams, handle_cards_to_notes),
    "cardsInfo": (CardsIdsParams, handle_cards_info),
    "suspend": (CardsIdsParams, handle_suspend),
    "unsuspend": (CardsIdsParams, handle_unsuspend),
    "areSuspended": (CardsIdsParams, handle_are_suspended),
    "areDue": (CardsIdsParams, handle_are_due),
    "getIntervals": (GetIntervalsParams, handle_get_intervals),
    "getMediaDirPath": (EmptyParams, handle_get_media_dir_path),
    "storeMediaFile": (StoreMediaFileParams, handle_store_media_file),
    "retrieveMediaFile": (FilenameParams, handle_retrieve_media_file),
    "deleteMediaFile": (FilenameParams, handle_delete_media_file),
    "importPackage": (ImportPackageParams, handle_import_package),
    "exportPackage": (ExportPackageParams, handle_export_package),
    "multi": (MultiParams, handle_multi),
}


async def dispatch(action: str, params: JsonObject, wrapper: AnkiWrapper) -> Any:
    entry = ACTION_HANDLERS.get(action)
    if not entry:
        logger.warning(f"Unsupported action requested: {action}")
        raise ValueError(f"Unsupported action: {action}")
    model_cls, handler = entry
    try:
        validated = model_cls(**params)
    except ValidationError as e:
        logger.warning(f"Validation error in {action}: {e}")
        raise ValueError(str(e)) from e
    result = handler(wrapper, validated)
    if asyncio.iscoroutine(result):
        result = await result
    return result
