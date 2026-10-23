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
    AnswerCardsParams,
    ApiReflectParams,
    CardReviewsParams,
    CardsIdsParams,
    ChangeDeckParams,
    CloneDeckConfigIdParams,
    CreateDeckParams,
    CreateModelParams,
    CredentialsParams,
    DeckIdParams,
    DeckNameParams,
    DeleteDecksParams,
    EmptyParams,
    ExportPackageParams,
    FilenameParams,
    FindAndReplaceInModelsParams,
    FindCardsParams,
    FindNotesParams,
    GetCollectionStatsHTMLParams,
    GetDeckConfigParams,
    GetDecksParams,
    GetDeckStatsParams,
    GetIntervalsParams,
    GetMediaFilesNamesParams,
    GetNoteTagsParams,
    ImportPackageParams,
    InsertReviewsParams,
    JsonObject,
    JsonValue,
    ModelFieldAddParams,
    ModelFieldRemoveParams,
    ModelFieldRenameParams,
    ModelFieldRepositionParams,
    ModelFieldSetDescriptionParams,
    ModelFieldSetFontParams,
    ModelFieldSetFontSizeParams,
    ModelIdParams,
    ModelNameParams,
    ModelStylingUpdateParams,
    ModelTemplateAddParams,
    ModelTemplateRemoveParams,
    ModelTemplateRenameParams,
    ModelTemplateRepositionParams,
    ModelTemplateUpdateParams,
    MultiParams,
    NotesIdsParams,
    RemoveDeckConfigIdParams,
    ReplaceTagsInAllNotesParams,
    ReplaceTagsParams,
    SaveDeckConfigParams,
    SetDeckConfigIdParams,
    SetEaseFactorsParams,
    SetSpecificValueOfCardParams,
    StoreMediaFileParams,
    SuspendedParams,
    UpdateNoteFieldsParams,
    UpdateNoteParams,
    UpdateNoteTagsParams,
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


async def handle_api_reflect(wrapper: AnkiWrapper, params: ApiReflectParams) -> JsonObject:
    """Introspect the registered actions (upstream parity).

    Only the "actions" scope is supported. Upstream silently skips non-string
    entries in actions; pydantic's list[str] rejects them with a validation
    error instead, which is consistent with this server's extra="forbid"
    philosophy.
    """
    _ = wrapper
    result: JsonObject = {"scopes": []}
    if "actions" in params.scopes:
        requested = params.actions if params.actions is not None else list(ACTION_HANDLERS)
        result["scopes"] = ["actions"]
        result["actions"] = [a for a in requested if a in ACTION_HANDLERS]
    return result


async def handle_reload_collection(wrapper: AnkiWrapper, params: EmptyParams) -> None:
    _ = (wrapper, params)
    await _run(wrapper.reload_collection)


async def handle_request_permission(wrapper: AnkiWrapper, params: EmptyParams) -> JsonObject:
    _ = (wrapper, params)
    return await _run(wrapper.request_permission)


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


async def handle_deck_name_from_id(wrapper: AnkiWrapper, params: DeckIdParams) -> str:
    return await _run(wrapper.deck_name_from_id, params.deckId)


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


async def handle_model_name_from_id(wrapper: AnkiWrapper, params: ModelIdParams) -> str:
    return await _run(wrapper.model_name_from_id, params.modelId)


async def handle_model_field_names(wrapper: AnkiWrapper, params: ModelNameParams) -> list[str]:
    return await _run(wrapper.model_field_names, params.modelName)


async def handle_model_fields_on_templates(wrapper: AnkiWrapper, params: ModelNameParams) -> Any:
    return await _run(wrapper.model_fields_on_templates, params.modelName)


async def handle_create_model(wrapper: AnkiWrapper, params: CreateModelParams) -> JsonObject:
    return await _run(
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


async def handle_model_field_add(wrapper: AnkiWrapper, params: ModelFieldAddParams) -> None:
    await _run(wrapper.model_field_add, params.modelName, params.fieldName, params.index)


async def handle_model_field_remove(wrapper: AnkiWrapper, params: ModelFieldRemoveParams) -> None:
    await _run(wrapper.model_field_remove, params.modelName, params.fieldName)


async def handle_model_field_rename(wrapper: AnkiWrapper, params: ModelFieldRenameParams) -> None:
    await _run(
        wrapper.model_field_rename, params.modelName, params.oldFieldName, params.newFieldName
    )


async def handle_model_field_reposition(
    wrapper: AnkiWrapper, params: ModelFieldRepositionParams
) -> None:
    await _run(wrapper.model_field_reposition, params.modelName, params.fieldName, params.index)


async def handle_model_field_set_font(
    wrapper: AnkiWrapper, params: ModelFieldSetFontParams
) -> None:
    await _run(wrapper.model_field_set_font, params.modelName, params.fieldName, params.font)


async def handle_model_field_set_font_size(
    wrapper: AnkiWrapper, params: ModelFieldSetFontSizeParams
) -> None:
    await _run(
        wrapper.model_field_set_font_size, params.modelName, params.fieldName, params.fontSize
    )


async def handle_model_field_set_description(
    wrapper: AnkiWrapper, params: ModelFieldSetDescriptionParams
) -> bool:
    return await _run(
        wrapper.model_field_set_description,
        params.modelName,
        params.fieldName,
        params.description,
    )


async def handle_model_field_descriptions(
    wrapper: AnkiWrapper, params: ModelNameParams
) -> list[str]:
    return await _run(wrapper.model_field_descriptions, params.modelName)


async def handle_model_field_fonts(
    wrapper: AnkiWrapper, params: ModelNameParams
) -> dict[str, JsonObject]:
    return await _run(wrapper.model_field_fonts, params.modelName)


async def handle_model_template_add(wrapper: AnkiWrapper, params: ModelTemplateAddParams) -> None:
    await _run(wrapper.model_template_add, params.modelName, params.template)


async def handle_model_template_remove(
    wrapper: AnkiWrapper, params: ModelTemplateRemoveParams
) -> None:
    await _run(wrapper.model_template_remove, params.modelName, params.templateName)


async def handle_model_template_rename(
    wrapper: AnkiWrapper, params: ModelTemplateRenameParams
) -> None:
    await _run(
        wrapper.model_template_rename,
        params.modelName,
        params.oldTemplateName,
        params.newTemplateName,
    )


async def handle_model_template_reposition(
    wrapper: AnkiWrapper, params: ModelTemplateRepositionParams
) -> None:
    await _run(
        wrapper.model_template_reposition, params.modelName, params.templateName, params.index
    )


async def handle_find_and_replace_in_models(
    wrapper: AnkiWrapper, params: FindAndReplaceInModelsParams
) -> int:
    return await _run(
        wrapper.find_and_replace_in_models,
        params.modelName,
        params.findText,
        params.replaceText,
        params.front,
        params.back,
        params.css,
    )


async def handle_add_note(wrapper: AnkiWrapper, params: AddNoteParams) -> int | None:
    return await _run(wrapper.add_note, params.note)


async def handle_add_notes(wrapper: AnkiWrapper, params: AddNotesParams) -> list[int | None]:
    return await _run(wrapper.add_notes, params.notes)


async def handle_can_add_note(wrapper: AnkiWrapper, params: AddNoteParams) -> bool:
    return await _run(wrapper.can_add_note, params.note)


async def handle_can_add_notes(wrapper: AnkiWrapper, params: AddNotesParams) -> list[bool]:
    return await _run(wrapper.can_add_notes, params.notes)


async def handle_can_add_notes_with_error_detail(
    wrapper: AnkiWrapper, params: AddNotesParams
) -> list[JsonObject]:
    return await _run(wrapper.can_add_notes_with_error_detail, params.notes)


async def handle_update_note_fields(wrapper: AnkiWrapper, params: UpdateNoteFieldsParams) -> None:
    await _run(wrapper.update_note_fields, params.note.model_dump())


async def handle_update_note(wrapper: AnkiWrapper, params: UpdateNoteParams) -> None:
    await _run(wrapper.update_note, params.note.model_dump())


async def handle_add_tags(wrapper: AnkiWrapper, params: AddTagsParams) -> None:
    await _run(wrapper.add_tags, params.notes, params.tags)


async def handle_remove_tags(wrapper: AnkiWrapper, params: AddTagsParams) -> None:
    await _run(wrapper.remove_tags, params.notes, params.tags)


async def handle_get_tags(wrapper: AnkiWrapper, params: EmptyParams) -> list[str]:
    _ = (wrapper, params)
    return await _run(wrapper.get_tags)


async def handle_replace_tags(wrapper: AnkiWrapper, params: ReplaceTagsParams) -> None:
    await _run(wrapper.replace_tags, params.notes, params.tag_to_replace, params.replace_with_tag)


async def handle_replace_tags_in_all_notes(
    wrapper: AnkiWrapper, params: ReplaceTagsInAllNotesParams
) -> None:
    await _run(wrapper.replace_tags_in_all_notes, params.tag_to_replace, params.replace_with_tag)


async def handle_clear_unused_tags(wrapper: AnkiWrapper, params: EmptyParams) -> None:
    _ = (wrapper, params)
    await _run(wrapper.clear_unused_tags)


async def handle_get_note_tags(wrapper: AnkiWrapper, params: GetNoteTagsParams) -> list[str]:
    return await _run(wrapper.get_note_tags, params.note)


async def handle_update_note_tags(wrapper: AnkiWrapper, params: UpdateNoteTagsParams) -> None:
    tags_list = [params.tags] if isinstance(params.tags, str) else list(params.tags)
    await _run(wrapper.update_note_tags, params.note, tags_list)


async def handle_find_notes(wrapper: AnkiWrapper, params: FindNotesParams) -> list[int]:
    return await _run(wrapper.find_notes, params.query)


async def handle_notes_info(wrapper: AnkiWrapper, params: NotesIdsParams) -> list[JsonObject]:
    return await _run(wrapper.notes_info, params.notes)


async def handle_delete_notes(wrapper: AnkiWrapper, params: NotesIdsParams) -> None:
    await _run(wrapper.delete_notes, params.notes)


async def handle_remove_empty_notes(wrapper: AnkiWrapper, params: EmptyParams) -> None:
    _ = (wrapper, params)
    await _run(wrapper.remove_empty_notes)


async def handle_find_cards(wrapper: AnkiWrapper, params: FindCardsParams) -> list[int]:
    return await _run(wrapper.find_cards, params.query)


async def handle_cards_to_notes(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[int]:
    return await _run(wrapper.cards_to_notes, params.cards)


async def handle_cards_info(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[JsonObject]:
    return await _run(wrapper.cards_info, params.cards)


async def handle_cards_mod_time(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[JsonObject]:
    return await _run(wrapper.cards_mod_time, params.cards)


async def handle_suspend(wrapper: AnkiWrapper, params: CardsIdsParams) -> bool:
    return await _run(wrapper.suspend, params.cards)


async def handle_unsuspend(wrapper: AnkiWrapper, params: CardsIdsParams) -> bool:
    return await _run(wrapper.unsuspend, params.cards)


async def handle_suspended(wrapper: AnkiWrapper, params: SuspendedParams) -> bool:
    return await _run(wrapper.suspended, params.card)


async def handle_are_suspended(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[bool]:
    return await _run(wrapper.are_suspended, params.cards)


async def handle_are_due(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[bool]:
    return await _run(wrapper.are_due, params.cards)


async def handle_get_intervals(wrapper: AnkiWrapper, params: GetIntervalsParams) -> list[Any]:
    return await _run(wrapper.get_intervals, params.cards, params.complete)


async def handle_answer_cards(wrapper: AnkiWrapper, params: AnswerCardsParams) -> list[bool]:
    return await _run(wrapper.answer_cards, [answer.model_dump() for answer in params.answers])


async def handle_forget_cards(wrapper: AnkiWrapper, params: CardsIdsParams) -> None:
    await _run(wrapper.forget_cards, params.cards)


async def handle_relearn_cards(wrapper: AnkiWrapper, params: CardsIdsParams) -> None:
    await _run(wrapper.relearn_cards, params.cards)


async def handle_set_ease_factors(wrapper: AnkiWrapper, params: SetEaseFactorsParams) -> list[bool]:
    return await _run(wrapper.set_ease_factors, params.cards, params.easeFactors)


async def handle_get_ease_factors(wrapper: AnkiWrapper, params: CardsIdsParams) -> list[int | None]:
    return await _run(wrapper.get_ease_factors, params.cards)


async def handle_set_specific_value_of_card(
    wrapper: AnkiWrapper, params: SetSpecificValueOfCardParams
) -> Any:
    return await _run(
        wrapper.set_specific_value_of_card,
        params.card,
        params.keys,
        params.newValues,
        params.warning_check,
    )


async def handle_card_reviews(wrapper: AnkiWrapper, params: CardReviewsParams) -> list[JsonValue]:
    return await _run(wrapper.card_reviews, params.deck, params.startID)


async def handle_get_reviews_of_cards(
    wrapper: AnkiWrapper, params: CardsIdsParams
) -> dict[int, list[JsonObject]]:
    return await _run(wrapper.get_reviews_of_cards, params.cards)


async def handle_get_latest_review_id(wrapper: AnkiWrapper, params: DeckNameParams) -> int:
    return await _run(wrapper.get_latest_review_id, params.deck)


async def handle_get_num_cards_reviewed_today(wrapper: AnkiWrapper, params: EmptyParams) -> int:
    _ = (wrapper, params)
    return await _run(wrapper.get_num_cards_reviewed_today)


async def handle_get_num_cards_reviewed_by_day(
    wrapper: AnkiWrapper, params: EmptyParams
) -> list[JsonValue]:
    _ = (wrapper, params)
    return await _run(wrapper.get_num_cards_reviewed_by_day)


async def handle_insert_reviews(wrapper: AnkiWrapper, params: InsertReviewsParams) -> None:
    await _run(wrapper.insert_reviews, params.reviews)


async def handle_get_deck_stats(
    wrapper: AnkiWrapper, params: GetDeckStatsParams
) -> dict[int, JsonObject]:
    return await _run(wrapper.get_deck_stats, params.decks)


async def handle_get_collection_stats_html(
    wrapper: AnkiWrapper, params: GetCollectionStatsHTMLParams
) -> str:
    return await _run(wrapper.get_collection_stats_html, params.wholeCollection)


async def handle_get_media_dir_path(wrapper: AnkiWrapper, params: EmptyParams) -> str:
    _ = (wrapper, params)
    return await _run(wrapper.get_media_dir_path)


async def handle_get_media_files_names(
    wrapper: AnkiWrapper, params: GetMediaFilesNamesParams
) -> list[str]:
    return await _run(wrapper.get_media_files_names, params.pattern)


async def handle_store_media_file(wrapper: AnkiWrapper, params: StoreMediaFileParams) -> None:
    await _run(wrapper.store_media_file, params.filename, params.data, params.url, params.path)


async def handle_retrieve_media_file(wrapper: AnkiWrapper, params: FilenameParams) -> str | None:
    return await _run(wrapper.retrieve_media_file, params.filename)


async def handle_delete_media_file(wrapper: AnkiWrapper, params: FilenameParams) -> None:
    await _run(wrapper.delete_media_file, params.filename)


async def handle_import_package(wrapper: AnkiWrapper, params: ImportPackageParams) -> JsonObject:
    return await _run(wrapper.import_package, params.path)


async def handle_export_package(wrapper: AnkiWrapper, params: ExportPackageParams) -> None:
    await _run(wrapper.export_package, params.deck, params.path, params.includeSched)


async def handle_multi(wrapper: AnkiWrapper, params: MultiParams) -> list[Any]:
    """Execute multiple actions, one reply per action (upstream parity).

    Upstream runs each entry through its generic handler, which formats the
    reply from the entry's own `version` (defaulting to 4): successes are the
    bare value for version <= 4 and {"result": ..., "error": null} for
    version >= 5; failures are always {"result": null, "error": "<msg>"}
    regardless of version (upstream's format_exception_reply ignores the
    version). E2E issue P2-4: failure entries previously omitted the
    "result": null key, breaking envelope-parsing clients.
    """
    results: list[Any] = []
    for action in params.actions:
        if not isinstance(action, dict):
            results.append(
                {
                    "result": None,
                    "error": f"Invalid action: expected object, got {type(action).__name__}",
                }
            )
            continue
        action_name = action.get("action", "")
        if not isinstance(action_name, str):
            results.append({"result": None, "error": "Invalid action: 'action' must be a string"})
            continue
        entry = ACTION_HANDLERS.get(action_name)
        if not entry:
            # Same wording as the top-level dispatch (E2E P3-3: the shapes
            # previously disagreed: "Unknown action" vs "Unsupported action").
            results.append({"result": None, "error": f"Unsupported action: {action_name}"})
            continue
        model_cls, handler = entry
        action_params = action.get("params", {})
        if not isinstance(action_params, dict):
            results.append(
                {"result": None, "error": f"Invalid params for {action_name}: expected object"}
            )
            continue
        version = action.get("version", 4)
        if not isinstance(version, int) or isinstance(version, bool):
            results.append(
                {"result": None, "error": "Invalid action: 'version' must be an integer"}
            )
            continue
        try:
            validated = model_cls(**action_params)
            result = handler(wrapper, validated)
            if asyncio.iscoroutine(result):
                result = await result
            if version >= 5:
                results.append({"result": result, "error": None})
            else:
                results.append(result)
        except Exception as e:
            # Per-action failure does not abort the whole multi call; the
            # failure is reported in the per-action error envelope.
            results.append({"result": None, "error": str(e)})
    return results


# Registry mapping AnkiConnect action names to (pydantic param model, handler).
ACTION_HANDLERS: dict[str, tuple[type[BaseModel], Handler[Any]]] = {
    "version": (EmptyParams, handle_version),
    "sync": (CredentialsParams, handle_sync),
    "syncStatus": (CredentialsParams, handle_sync_status),
    "syncMedia": (CredentialsParams, handle_sync_media),
    "apiReflect": (ApiReflectParams, handle_api_reflect),
    "reloadCollection": (EmptyParams, handle_reload_collection),
    "requestPermission": (EmptyParams, handle_request_permission),
    "deckNames": (EmptyParams, handle_deck_names),
    "deckNamesAndIds": (EmptyParams, handle_deck_names_and_ids),
    "deckNameFromId": (DeckIdParams, handle_deck_name_from_id),
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
    "modelNameFromId": (ModelIdParams, handle_model_name_from_id),
    "modelFieldNames": (ModelNameParams, handle_model_field_names),
    "modelFieldsOnTemplates": (ModelNameParams, handle_model_fields_on_templates),
    "createModel": (CreateModelParams, handle_create_model),
    "modelTemplates": (ModelNameParams, handle_model_templates),
    "modelStyling": (ModelNameParams, handle_model_styling),
    "updateModelTemplates": (ModelTemplateUpdateParams, handle_update_model_templates),
    "updateModelStyling": (ModelStylingUpdateParams, handle_update_model_styling),
    "modelFieldAdd": (ModelFieldAddParams, handle_model_field_add),
    "modelFieldRemove": (ModelFieldRemoveParams, handle_model_field_remove),
    "modelFieldRename": (ModelFieldRenameParams, handle_model_field_rename),
    "modelFieldReposition": (ModelFieldRepositionParams, handle_model_field_reposition),
    "modelFieldSetFont": (ModelFieldSetFontParams, handle_model_field_set_font),
    "modelFieldSetFontSize": (ModelFieldSetFontSizeParams, handle_model_field_set_font_size),
    "modelFieldSetDescription": (
        ModelFieldSetDescriptionParams,
        handle_model_field_set_description,
    ),
    "modelFieldDescriptions": (ModelNameParams, handle_model_field_descriptions),
    "modelFieldFonts": (ModelNameParams, handle_model_field_fonts),
    "modelTemplateAdd": (ModelTemplateAddParams, handle_model_template_add),
    "modelTemplateRemove": (ModelTemplateRemoveParams, handle_model_template_remove),
    "modelTemplateRename": (ModelTemplateRenameParams, handle_model_template_rename),
    "modelTemplateReposition": (ModelTemplateRepositionParams, handle_model_template_reposition),
    "findAndReplaceInModels": (FindAndReplaceInModelsParams, handle_find_and_replace_in_models),
    "addNote": (AddNoteParams, handle_add_note),
    "addNotes": (AddNotesParams, handle_add_notes),
    "canAddNote": (AddNoteParams, handle_can_add_note),
    "canAddNotes": (AddNotesParams, handle_can_add_notes),
    "canAddNotesWithErrorDetail": (AddNotesParams, handle_can_add_notes_with_error_detail),
    "updateNoteFields": (UpdateNoteFieldsParams, handle_update_note_fields),
    "updateNote": (UpdateNoteParams, handle_update_note),
    "addTags": (AddTagsParams, handle_add_tags),
    "removeTags": (AddTagsParams, handle_remove_tags),
    "getTags": (EmptyParams, handle_get_tags),
    "replaceTags": (ReplaceTagsParams, handle_replace_tags),
    "replaceTagsInAllNotes": (ReplaceTagsInAllNotesParams, handle_replace_tags_in_all_notes),
    "clearUnusedTags": (EmptyParams, handle_clear_unused_tags),
    "getNoteTags": (GetNoteTagsParams, handle_get_note_tags),
    "updateNoteTags": (UpdateNoteTagsParams, handle_update_note_tags),
    "findNotes": (FindNotesParams, handle_find_notes),
    "notesInfo": (NotesIdsParams, handle_notes_info),
    "deleteNotes": (NotesIdsParams, handle_delete_notes),
    "removeEmptyNotes": (EmptyParams, handle_remove_empty_notes),
    "findCards": (FindCardsParams, handle_find_cards),
    "cardsToNotes": (CardsIdsParams, handle_cards_to_notes),
    "cardsInfo": (CardsIdsParams, handle_cards_info),
    "cardsModTime": (CardsIdsParams, handle_cards_mod_time),
    "suspend": (CardsIdsParams, handle_suspend),
    "unsuspend": (CardsIdsParams, handle_unsuspend),
    "suspended": (SuspendedParams, handle_suspended),
    "areSuspended": (CardsIdsParams, handle_are_suspended),
    "areDue": (CardsIdsParams, handle_are_due),
    "getIntervals": (GetIntervalsParams, handle_get_intervals),
    "answerCards": (AnswerCardsParams, handle_answer_cards),
    "forgetCards": (CardsIdsParams, handle_forget_cards),
    "relearnCards": (CardsIdsParams, handle_relearn_cards),
    "setEaseFactors": (SetEaseFactorsParams, handle_set_ease_factors),
    "getEaseFactors": (CardsIdsParams, handle_get_ease_factors),
    "setSpecificValueOfCard": (SetSpecificValueOfCardParams, handle_set_specific_value_of_card),
    "cardReviews": (CardReviewsParams, handle_card_reviews),
    "getReviewsOfCards": (CardsIdsParams, handle_get_reviews_of_cards),
    "getLatestReviewID": (DeckNameParams, handle_get_latest_review_id),
    "getNumCardsReviewedToday": (EmptyParams, handle_get_num_cards_reviewed_today),
    "getNumCardsReviewedByDay": (EmptyParams, handle_get_num_cards_reviewed_by_day),
    "insertReviews": (InsertReviewsParams, handle_insert_reviews),
    "getDeckStats": (GetDeckStatsParams, handle_get_deck_stats),
    "getCollectionStatsHTML": (GetCollectionStatsHTMLParams, handle_get_collection_stats_html),
    "getMediaDirPath": (EmptyParams, handle_get_media_dir_path),
    "getMediaFilesNames": (GetMediaFilesNamesParams, handle_get_media_files_names),
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
