import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from anki_connect_server.anki_wrapper import AnkiWrapper
from anki_connect_server.types import JsonObject

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


# A handler takes (wrapper, params) and returns a JSON-serialisable value or
# coroutine resolving to one. The return is Any because handlers return a wide
# variety of concrete types (int, str, list[int], dict[str, JsonObject], None,
# etc.) and the protocol would otherwise need a union of dozens of overloads.
type Handler = Callable[[AnkiWrapper, JsonObject], Awaitable[Any] | Any]


def require_params(params: JsonObject, *required_keys: str) -> None:
    missing = [k for k in required_keys if k not in params or params[k] is None]
    if missing:
        raise ValidationError(f"Missing required parameters: {', '.join(missing)}")


def _get_str(params: JsonObject, key: str, default: str = "") -> str:
    value = params.get(key, default)
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _get_bool(params: JsonObject, key: str, default: bool = False) -> bool:
    value = params.get(key, default)
    if isinstance(value, bool):
        return value
    return default


def _get_int(params: JsonObject, key: str, default: int = 0) -> int:
    value = params.get(key, default)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return default


def _get_int_list(params: JsonObject, key: str) -> list[int]:
    value = params.get(key, [])
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if isinstance(item, int) and not isinstance(item, bool):
            result.append(item)
        elif isinstance(item, float) and item.is_integer():
            result.append(int(item))
    return result


def _get_str_list(params: JsonObject, key: str) -> list[str]:
    value = params.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _get_optional_str(params: JsonObject, key: str) -> str | None:
    value = params.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _get_obj(params: JsonObject, key: str) -> JsonObject:
    value = params.get(key, {})
    if isinstance(value, dict):
        return value
    return {}


async def _run[R](func: Callable[..., R], *args: object, **kwargs: object) -> R:
    """Run a blocking AnkiWrapper method in a worker thread.

    The handlers are async so they can be composed by handle_multi and tested
    with await, but the underlying AnkiWrapper methods are blocking. Running
    them in asyncio.to_thread keeps the event loop responsive during long
    collection operations (find_cards over a large collection, sync, etc.).
    """
    return await asyncio.to_thread(func, *args, **kwargs)


API_VERSION = 6


async def handle_version(wrapper: AnkiWrapper, params: JsonObject) -> int:
    _ = (wrapper, params)
    return API_VERSION


async def handle_sync(wrapper: AnkiWrapper, params: JsonObject) -> str:
    endpoint = _get_optional_str(params, "endpoint")
    username = _get_optional_str(params, "username")
    password = _get_optional_str(params, "password")
    return await _run(wrapper.sync_to_ankiweb, username, password, endpoint)


async def handle_sync_status(wrapper: AnkiWrapper, params: JsonObject) -> JsonObject:
    endpoint = _get_optional_str(params, "endpoint")
    username = _get_optional_str(params, "username")
    password = _get_optional_str(params, "password")
    return await _run(wrapper.sync_status, username=username, password=password, endpoint=endpoint)


async def handle_sync_media(wrapper: AnkiWrapper, params: JsonObject) -> str:
    endpoint = _get_optional_str(params, "endpoint")
    username = _get_optional_str(params, "username")
    password = _get_optional_str(params, "password")
    return await _run(wrapper.sync_media_only, username, password, endpoint)


async def handle_deck_names(wrapper: AnkiWrapper, params: JsonObject) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.deck_names)


async def handle_deck_names_and_ids(wrapper: AnkiWrapper, params: JsonObject) -> dict[str, int]:
    _ = (wrapper, params)
    return await _run(wrapper.deck_names_and_ids)


async def handle_get_decks(wrapper: AnkiWrapper, params: JsonObject) -> dict[str, list[int]]:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.get_decks, cards)


async def handle_create_deck(wrapper: AnkiWrapper, params: JsonObject) -> int:
    require_params(params, "deck")
    deck = _get_str(params, "deck")
    if not deck:
        raise ValidationError("Deck name cannot be empty")
    return await _run(wrapper.create_deck, deck)


async def handle_change_deck(wrapper: AnkiWrapper, params: JsonObject) -> None:
    cards = _get_int_list(params, "cards")
    deck = _get_str(params, "deck")
    await _run(wrapper.change_deck, cards, deck)


async def handle_delete_decks(wrapper: AnkiWrapper, params: JsonObject) -> None:
    decks = _get_str_list(params, "decks")
    cards_too = _get_bool(params, "cardsToo")
    await _run(wrapper.delete_decks, decks, cards_too)


async def handle_get_deck_config(wrapper: AnkiWrapper, params: JsonObject) -> JsonObject:
    deck = _get_str(params, "deck")
    return await _run(wrapper.get_deck_config, deck)


async def handle_save_deck_config(wrapper: AnkiWrapper, params: JsonObject) -> bool:
    config = _get_obj(params, "config")
    return await _run(wrapper.save_deck_config, config)


async def handle_set_deck_config_id(wrapper: AnkiWrapper, params: JsonObject) -> bool:
    decks = _get_str_list(params, "decks")
    config_id = _get_int(params, "configId", 1)
    return await _run(wrapper.set_deck_config_id, decks, config_id)


async def handle_clone_deck_config_id(wrapper: AnkiWrapper, params: JsonObject) -> int:
    name = _get_str(params, "name")
    clone_from = _get_int(params, "cloneFrom", 1)
    return await _run(wrapper.clone_deck_config_id, name, clone_from)


async def handle_remove_deck_config_id(wrapper: AnkiWrapper, params: JsonObject) -> bool:
    config_id = _get_int(params, "configId", 1)
    return await _run(wrapper.remove_deck_config_id, config_id)


async def handle_model_names(wrapper: AnkiWrapper, params: JsonObject) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.model_names)


async def handle_model_names_and_ids(wrapper: AnkiWrapper, params: JsonObject) -> dict[str, int]:
    _ = (wrapper, params)
    return await _run(wrapper.model_names_and_ids)


async def handle_model_field_names(wrapper: AnkiWrapper, params: JsonObject) -> list[str]:
    model_name = _get_str(params, "modelName")
    return await _run(wrapper.model_field_names, model_name)


async def handle_model_fields_on_templates(wrapper: AnkiWrapper, params: JsonObject) -> Any:
    model_name = _get_str(params, "modelName")
    return await _run(wrapper.model_fields_on_templates, model_name)


async def handle_create_model(wrapper: AnkiWrapper, params: JsonObject) -> None:
    model_name = _get_str(params, "modelName")
    in_order_fields = _get_str_list(params, "inOrderFields")
    raw_templates = params.get("cardTemplates", [])
    card_templates: list[dict[str, str]] = []
    if isinstance(raw_templates, list):
        card_templates.extend(
            {
                "Name": str(tmpl.get("Name", "")),
                "Front": str(tmpl.get("Front", "")),
                "Back": str(tmpl.get("Back", "")),
            }
            for tmpl in raw_templates
            if isinstance(tmpl, dict)
        )
    css = _get_str(params, "css")
    is_cloze = _get_bool(params, "isCloze")
    await _run(wrapper.create_model, model_name, in_order_fields, card_templates, css, is_cloze)


async def handle_model_templates(wrapper: AnkiWrapper, params: JsonObject) -> Any:
    model_name = _get_str(params, "modelName")
    return await _run(wrapper.model_templates, model_name)


async def handle_model_styling(wrapper: AnkiWrapper, params: JsonObject) -> JsonObject:
    model_name = _get_str(params, "modelName")
    return await _run(wrapper.model_styling, model_name)


async def handle_update_model_templates(wrapper: AnkiWrapper, params: JsonObject) -> None:
    model = _get_obj(params, "model")
    await _run(wrapper.update_model_templates, model)


async def handle_update_model_styling(wrapper: AnkiWrapper, params: JsonObject) -> None:
    model = _get_obj(params, "model")
    await _run(wrapper.update_model_styling, model)


async def handle_add_note(wrapper: AnkiWrapper, params: JsonObject) -> int | None:
    require_params(params, "note")
    note = params.get("note", {})
    if not isinstance(note, dict):
        raise ValidationError("note must be a dictionary")
    return await _run(wrapper.add_note, note)


async def handle_add_notes(wrapper: AnkiWrapper, params: JsonObject) -> list[int | None]:
    require_params(params, "notes")
    notes = params.get("notes", [])
    if not isinstance(notes, list):
        raise ValidationError("notes must be a list")
    return await _run(wrapper.add_notes, notes)


async def handle_can_add_notes(wrapper: AnkiWrapper, params: JsonObject) -> list[bool]:
    require_params(params, "notes")
    notes = params.get("notes", [])
    if not isinstance(notes, list):
        raise ValidationError("notes must be a list")
    return await _run(wrapper.can_add_notes, notes)


async def handle_update_note_fields(wrapper: AnkiWrapper, params: JsonObject) -> None:
    require_params(params, "note")
    note = params.get("note", {})
    if not isinstance(note, dict):
        raise ValidationError("note must be a dictionary")
    await _run(wrapper.update_note_fields, note)


async def handle_add_tags(wrapper: AnkiWrapper, params: JsonObject) -> None:
    notes = _get_int_list(params, "notes")
    tags = _get_str(params, "tags")
    await _run(wrapper.add_tags, notes, tags)


async def handle_remove_tags(wrapper: AnkiWrapper, params: JsonObject) -> None:
    notes = _get_int_list(params, "notes")
    tags = _get_str(params, "tags")
    await _run(wrapper.remove_tags, notes, tags)


async def handle_get_tags(wrapper: AnkiWrapper, params: JsonObject) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.get_tags)


async def handle_find_notes(wrapper: AnkiWrapper, params: JsonObject) -> list[int]:
    require_params(params, "query")
    query = _get_str(params, "query")
    return await _run(wrapper.find_notes, query)


async def handle_notes_info(wrapper: AnkiWrapper, params: JsonObject) -> list[JsonObject]:
    notes = _get_int_list(params, "notes")
    return await _run(wrapper.notes_info, notes)


async def handle_delete_notes(wrapper: AnkiWrapper, params: JsonObject) -> None:
    notes = _get_int_list(params, "notes")
    await _run(wrapper.delete_notes, notes)


async def handle_find_cards(wrapper: AnkiWrapper, params: JsonObject) -> list[int]:
    require_params(params, "query")
    query = _get_str(params, "query")
    return await _run(wrapper.find_cards, query)


async def handle_cards_to_notes(wrapper: AnkiWrapper, params: JsonObject) -> list[int]:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.cards_to_notes, cards)


async def handle_cards_info(wrapper: AnkiWrapper, params: JsonObject) -> list[JsonObject]:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.cards_info, cards)


async def handle_suspend(wrapper: AnkiWrapper, params: JsonObject) -> bool:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.suspend, cards)


async def handle_unsuspend(wrapper: AnkiWrapper, params: JsonObject) -> bool:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.unsuspend, cards)


async def handle_are_suspended(wrapper: AnkiWrapper, params: JsonObject) -> list[bool]:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.are_suspended, cards)


async def handle_are_due(wrapper: AnkiWrapper, params: JsonObject) -> list[bool]:
    cards = _get_int_list(params, "cards")
    return await _run(wrapper.are_due, cards)


async def handle_get_intervals(wrapper: AnkiWrapper, params: JsonObject) -> list[Any]:
    cards = _get_int_list(params, "cards")
    complete = _get_bool(params, "complete")
    return await _run(wrapper.get_intervals, cards, complete)


async def handle_get_media_dir_path(wrapper: AnkiWrapper, params: JsonObject) -> str:
    _ = (wrapper, params)
    return await _run(wrapper.get_media_dir_path)


async def handle_store_media_file(wrapper: AnkiWrapper, params: JsonObject) -> None:
    filename = _get_str(params, "filename")
    data = _get_str(params, "data")
    await _run(wrapper.store_media_file, filename, data)


async def handle_retrieve_media_file(wrapper: AnkiWrapper, params: JsonObject) -> str | None:
    filename = _get_str(params, "filename")
    return await _run(wrapper.retrieve_media_file, filename)


async def handle_delete_media_file(wrapper: AnkiWrapper, params: JsonObject) -> None:
    filename = _get_str(params, "filename")
    await _run(wrapper.delete_media_file, filename)


async def handle_import_package(wrapper: AnkiWrapper, params: JsonObject) -> JsonObject:
    path = _get_str(params, "path")
    return await _run(wrapper.import_package, path)


async def handle_export_package(wrapper: AnkiWrapper, params: JsonObject) -> None:
    deck = _get_str(params, "deck")
    path = _get_str(params, "path")
    include_sched = _get_bool(params, "includeSched")
    await _run(wrapper.export_package, deck, path, include_sched)


async def handle_multi(wrapper: AnkiWrapper, params: JsonObject) -> list[Any]:
    actions = params.get("actions", [])
    if not isinstance(actions, list):
        raise ValidationError("actions must be a list")
    results: list[Any] = []
    for action in actions:
        if not isinstance(action, dict):
            results.append(
                {"error": f"Invalid action: expected object, got {type(action).__name__}"}
            )
            continue
        action_name = _get_str(action, "action")
        action_params = _get_obj(action, "params")
        handler = ACTION_HANDLERS.get(action_name)
        if not handler:
            results.append({"error": f"Unknown action: {action_name}"})
            continue
        try:
            result = handler(wrapper, action_params)
            if asyncio.iscoroutine(result):
                result = await result
            results.append(result)
        except Exception as e:
            # Per-action failure does not abort the whole multi call.
            # AnkiConnect returns an error string per action.
            results.append({"error": str(e)})
    return results


ACTION_HANDLERS: dict[str, Handler] = {
    "version": handle_version,
    "sync": handle_sync,
    "syncStatus": handle_sync_status,
    "syncMedia": handle_sync_media,
    "deckNames": handle_deck_names,
    "deckNamesAndIds": handle_deck_names_and_ids,
    "getDecks": handle_get_decks,
    "createDeck": handle_create_deck,
    "changeDeck": handle_change_deck,
    "deleteDecks": handle_delete_decks,
    "getDeckConfig": handle_get_deck_config,
    "saveDeckConfig": handle_save_deck_config,
    "setDeckConfigId": handle_set_deck_config_id,
    "cloneDeckConfigId": handle_clone_deck_config_id,
    "removeDeckConfigId": handle_remove_deck_config_id,
    "modelNames": handle_model_names,
    "modelNamesAndIds": handle_model_names_and_ids,
    "modelFieldNames": handle_model_field_names,
    "modelFieldsOnTemplates": handle_model_fields_on_templates,
    "createModel": handle_create_model,
    "modelTemplates": handle_model_templates,
    "modelStyling": handle_model_styling,
    "updateModelTemplates": handle_update_model_templates,
    "updateModelStyling": handle_update_model_styling,
    "addNote": handle_add_note,
    "addNotes": handle_add_notes,
    "canAddNotes": handle_can_add_notes,
    "updateNoteFields": handle_update_note_fields,
    "addTags": handle_add_tags,
    "removeTags": handle_remove_tags,
    "getTags": handle_get_tags,
    "findNotes": handle_find_notes,
    "notesInfo": handle_notes_info,
    "deleteNotes": handle_delete_notes,
    "findCards": handle_find_cards,
    "cardsToNotes": handle_cards_to_notes,
    "cardsInfo": handle_cards_info,
    "suspend": handle_suspend,
    "unsuspend": handle_unsuspend,
    "areSuspended": handle_are_suspended,
    "areDue": handle_are_due,
    "getIntervals": handle_get_intervals,
    "getMediaDirPath": handle_get_media_dir_path,
    "storeMediaFile": handle_store_media_file,
    "retrieveMediaFile": handle_retrieve_media_file,
    "deleteMediaFile": handle_delete_media_file,
    "importPackage": handle_import_package,
    "exportPackage": handle_export_package,
    "multi": handle_multi,
}


async def dispatch(action: str, params: JsonObject, wrapper: AnkiWrapper) -> Any:
    handler = ACTION_HANDLERS.get(action)
    if not handler:
        logger.warning(f"Unsupported action requested: {action}")
        raise ValueError(f"Unsupported action: {action}")
    try:
        result = handler(wrapper, params)
        if asyncio.iscoroutine(result):
            result = await result
        return result
    except ValidationError as e:
        logger.warning(f"Validation error in {action}: {e}")
        raise ValueError(str(e)) from e
