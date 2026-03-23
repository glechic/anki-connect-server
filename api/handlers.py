import asyncio
import logging

from typing import Any, Optional
from anki_wrapper import AnkiWrapper

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    pass


def require_params(params: dict, *required_keys: str) -> None:
    missing = [k for k in required_keys if k not in params or params[k] is None]
    if missing:
        raise ValidationError(f"Missing required parameters: {', '.join(missing)}")


API_VERSION = 6


async def handle_version(wrapper: AnkiWrapper, params: dict) -> int:
    return API_VERSION


async def handle_sync(wrapper: AnkiWrapper, params: dict) -> str:
    endpoint = params.get("endpoint")
    username = params.get("username")
    password = params.get("password")
    return await asyncio.to_thread(wrapper.sync_to_ankiweb, username, password, endpoint)


async def handle_sync_status(wrapper: AnkiWrapper, params: dict) -> dict:
    endpoint = params.get("endpoint")
    username = params.get("username")
    password = params.get("password")
    return wrapper.sync_status(username=username, password=password, endpoint=endpoint)


async def handle_sync_media(wrapper: AnkiWrapper, params: dict) -> str:
    endpoint = params.get("endpoint")
    username = params.get("username")
    password = params.get("password")
    return await asyncio.to_thread(wrapper.sync_media_only, username, password, endpoint)


async def handle_deck_names(wrapper: AnkiWrapper, params: dict) -> list[str]:
    return wrapper.deck_names()


async def handle_deck_names_and_ids(wrapper: AnkiWrapper, params: dict) -> dict[str, int]:
    return wrapper.deck_names_and_ids()


async def handle_get_decks(wrapper: AnkiWrapper, params: dict) -> dict[str, list[int]]:
    cards = params.get("cards", [])
    return wrapper.get_decks(cards)


async def handle_create_deck(wrapper: AnkiWrapper, params: dict) -> int:
    require_params(params, "deck")
    deck = params.get("deck", "")
    if not deck:
        raise ValidationError("Deck name cannot be empty")
    return wrapper.create_deck(deck)


async def handle_change_deck(wrapper: AnkiWrapper, params: dict) -> None:
    cards = params.get("cards", [])
    deck = params.get("deck", "")
    wrapper.change_deck(cards, deck)


async def handle_delete_decks(wrapper: AnkiWrapper, params: dict) -> None:
    decks = params.get("decks", [])
    cards_too = params.get("cardsToo", False)
    wrapper.delete_decks(decks, cards_too)


async def handle_get_deck_config(wrapper: AnkiWrapper, params: dict) -> dict:
    deck = params.get("deck", "")
    return wrapper.get_deck_config(deck)


async def handle_save_deck_config(wrapper: AnkiWrapper, params: dict) -> bool:
    config = params.get("config", {})
    return wrapper.save_deck_config(config)


async def handle_set_deck_config_id(wrapper: AnkiWrapper, params: dict) -> bool:
    decks = params.get("decks", [])
    config_id = params.get("configId", 1)
    return wrapper.set_deck_config_id(decks, config_id)


async def handle_clone_deck_config_id(wrapper: AnkiWrapper, params: dict) -> int:
    name = params.get("name", "")
    clone_from = params.get("cloneFrom", 1)
    return wrapper.clone_deck_config_id(name, clone_from)


async def handle_remove_deck_config_id(wrapper: AnkiWrapper, params: dict) -> bool:
    config_id = params.get("configId", 1)
    return wrapper.remove_deck_config_id(config_id)


async def handle_model_names(wrapper: AnkiWrapper, params: dict) -> list[str]:
    return wrapper.model_names()


async def handle_model_names_and_ids(wrapper: AnkiWrapper, params: dict) -> dict[str, int]:
    return wrapper.model_names_and_ids()


async def handle_model_field_names(wrapper: AnkiWrapper, params: dict) -> list[str]:
    model_name = params.get("modelName", "")
    return wrapper.model_field_names(model_name)


async def handle_model_fields_on_templates(wrapper: AnkiWrapper, params: dict) -> dict:
    model_name = params.get("modelName", "")
    return wrapper.model_fields_on_templates(model_name)


async def handle_create_model(wrapper: AnkiWrapper, params: dict) -> None:
    model_name = params.get("modelName", "")
    in_order_fields = params.get("inOrderFields", [])
    card_templates = params.get("cardTemplates", [])
    css = params.get("css", "")
    is_cloze = params.get("isCloze", False)
    wrapper.create_model(model_name, in_order_fields, card_templates, css, is_cloze)


async def handle_model_templates(wrapper: AnkiWrapper, params: dict) -> dict:
    model_name = params.get("modelName", "")
    return wrapper.model_templates(model_name)


async def handle_model_styling(wrapper: AnkiWrapper, params: dict) -> dict:
    model_name = params.get("modelName", "")
    return wrapper.model_styling(model_name)


async def handle_update_model_templates(wrapper: AnkiWrapper, params: dict) -> None:
    model = params.get("model", {})
    wrapper.update_model_templates(model)


async def handle_update_model_styling(wrapper: AnkiWrapper, params: dict) -> None:
    model = params.get("model", {})
    wrapper.update_model_styling(model)


async def handle_add_note(wrapper: AnkiWrapper, params: dict) -> Optional[int]:
    require_params(params, "note")
    note = params.get("note", {})
    if not isinstance(note, dict):
        raise ValidationError("note must be a dictionary")
    return wrapper.add_note(note)


async def handle_add_notes(wrapper: AnkiWrapper, params: dict) -> list[Optional[int]]:
    require_params(params, "notes")
    notes = params.get("notes", [])
    if not isinstance(notes, list):
        raise ValidationError("notes must be a list")
    return wrapper.add_notes(notes)


async def handle_can_add_notes(wrapper: AnkiWrapper, params: dict) -> list[bool]:
    require_params(params, "notes")
    notes = params.get("notes", [])
    if not isinstance(notes, list):
        raise ValidationError("notes must be a list")
    return wrapper.can_add_notes(notes)


async def handle_update_note_fields(wrapper: AnkiWrapper, params: dict) -> None:
    require_params(params, "note")
    note = params.get("note", {})
    if not isinstance(note, dict):
        raise ValidationError("note must be a dictionary")
    wrapper.update_note_fields(note)


async def handle_add_tags(wrapper: AnkiWrapper, params: dict) -> None:
    notes = params.get("notes", [])
    tags = params.get("tags", "")
    wrapper.add_tags(notes, tags)


async def handle_remove_tags(wrapper: AnkiWrapper, params: dict) -> None:
    notes = params.get("notes", [])
    tags = params.get("tags", "")
    wrapper.remove_tags(notes, tags)


async def handle_get_tags(wrapper: AnkiWrapper, params: dict) -> list[str]:
    return wrapper.get_tags()


async def handle_find_notes(wrapper: AnkiWrapper, params: dict) -> list[int]:
    query = params.get("query", "")
    return wrapper.find_notes(query)


async def handle_notes_info(wrapper: AnkiWrapper, params: dict) -> list[dict]:
    notes = params.get("notes", [])
    return wrapper.notes_info(notes)


async def handle_delete_notes(wrapper: AnkiWrapper, params: dict) -> None:
    notes = params.get("notes", [])
    wrapper.delete_notes(notes)


async def handle_find_cards(wrapper: AnkiWrapper, params: dict) -> list[int]:
    query = params.get("query", "")
    return wrapper.find_cards(query)


async def handle_cards_to_notes(wrapper: AnkiWrapper, params: dict) -> list[int]:
    cards = params.get("cards", [])
    return wrapper.cards_to_notes(cards)


async def handle_cards_info(wrapper: AnkiWrapper, params: dict) -> list[dict]:
    cards = params.get("cards", [])
    return wrapper.cards_info(cards)


async def handle_suspend(wrapper: AnkiWrapper, params: dict) -> bool:
    cards = params.get("cards", [])
    return wrapper.suspend(cards)


async def handle_unsuspend(wrapper: AnkiWrapper, params: dict) -> bool:
    cards = params.get("cards", [])
    return wrapper.unsuspend(cards)


async def handle_are_suspended(wrapper: AnkiWrapper, params: dict) -> list[bool]:
    cards = params.get("cards", [])
    return wrapper.are_suspended(cards)


async def handle_are_due(wrapper: AnkiWrapper, params: dict) -> list[bool]:
    cards = params.get("cards", [])
    return wrapper.are_due(cards)


async def handle_get_intervals(wrapper: AnkiWrapper, params: dict) -> list[Any]:
    cards = params.get("cards", [])
    complete = params.get("complete", False)
    return wrapper.get_intervals(cards, complete)


async def handle_get_media_dir_path(wrapper: AnkiWrapper, params: dict) -> str:
    return wrapper.get_media_dir_path()


async def handle_store_media_file(wrapper: AnkiWrapper, params: dict) -> None:
    filename = params.get("filename", "")
    data = params.get("data", "")
    wrapper.store_media_file(filename, data)


async def handle_retrieve_media_file(wrapper: AnkiWrapper, params: dict) -> Optional[str]:
    filename = params.get("filename", "")
    return wrapper.retrieve_media_file(filename)


async def handle_delete_media_file(wrapper: AnkiWrapper, params: dict) -> None:
    filename = params.get("filename", "")
    wrapper.delete_media_file(filename)


async def handle_import_package(wrapper: AnkiWrapper, params: dict) -> dict:
    path = params.get("path", "")
    return wrapper.import_package(path)


async def handle_export_package(wrapper: AnkiWrapper, params: dict) -> None:
    deck = params.get("deck", "")
    path = params.get("path", "")
    include_sched = params.get("includeSched", False)
    wrapper.export_package(deck, path, include_sched)


async def handle_multi(wrapper: AnkiWrapper, params: dict) -> list[Any]:
    actions = params.get("actions", [])
    results = []
    for action in actions:
        action_name = action.get("action", "")
        action_params = action.get("params", {})
        handler = ACTION_HANDLERS.get(action_name)
        if handler:
            result = await handler(wrapper, action_params)
            results.append(result)
        else:
            results.append({"error": f"Unknown action: {action_name}"})
    return results


ACTION_HANDLERS = {
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


async def dispatch(action: str, params: dict, wrapper: AnkiWrapper) -> Any:
    handler = ACTION_HANDLERS.get(action)
    if not handler:
        logger.warning(f"Unsupported action requested: {action}")
        raise ValueError(f"Unsupported action: {action}")
    try:
        return await handler(wrapper, params)
    except ValidationError as e:
        logger.warning(f"Validation error in {action}: {e}")
        raise ValueError(str(e))