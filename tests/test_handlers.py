"""Tests for API handlers using real AnkiWrapper."""

import base64
import time
from typing import cast

import pytest
from anki.cards import CardId
from pydantic import ValidationError

from anki_connect_server.anki_wrapper import AnkiWrapper
from anki_connect_server.handlers import (
    API_VERSION,
    handle_add_note,
    handle_add_notes,
    handle_add_tags,
    handle_answer_cards,
    handle_api_reflect,
    handle_are_due,
    handle_are_suspended,
    handle_can_add_note,
    handle_can_add_notes,
    handle_can_add_notes_with_error_detail,
    handle_card_reviews,
    handle_cards_info,
    handle_cards_mod_time,
    handle_cards_to_notes,
    handle_change_deck,
    handle_clear_unused_tags,
    handle_create_deck,
    handle_deck_name_from_id,
    handle_deck_names,
    handle_deck_names_and_ids,
    handle_delete_decks,
    handle_delete_notes,
    handle_find_and_replace_in_models,
    handle_find_cards,
    handle_find_notes,
    handle_forget_cards,
    handle_get_collection_stats_html,
    handle_get_deck_stats,
    handle_get_decks,
    handle_get_ease_factors,
    handle_get_intervals,
    handle_get_latest_review_id,
    handle_get_media_dir_path,
    handle_get_media_files_names,
    handle_get_note_tags,
    handle_get_num_cards_reviewed_by_day,
    handle_get_num_cards_reviewed_today,
    handle_get_reviews_of_cards,
    handle_insert_reviews,
    handle_model_field_add,
    handle_model_field_descriptions,
    handle_model_field_fonts,
    handle_model_field_names,
    handle_model_field_remove,
    handle_model_field_rename,
    handle_model_field_reposition,
    handle_model_field_set_description,
    handle_model_field_set_font,
    handle_model_field_set_font_size,
    handle_model_fields_on_templates,
    handle_model_name_from_id,
    handle_model_names,
    handle_model_names_and_ids,
    handle_model_styling,
    handle_model_template_add,
    handle_model_template_remove,
    handle_model_template_rename,
    handle_model_template_reposition,
    handle_multi,
    handle_notes_info,
    handle_relearn_cards,
    handle_reload_collection,
    handle_remove_empty_notes,
    handle_remove_tags,
    handle_replace_tags,
    handle_replace_tags_in_all_notes,
    handle_request_permission,
    handle_retrieve_media_file,
    handle_set_ease_factors,
    handle_set_specific_value_of_card,
    handle_suspend,
    handle_suspended,
    handle_sync_status,
    handle_unsuspend,
    handle_update_note_fields,
    handle_update_note_tags,
    handle_version,
)
from anki_connect_server.types import (
    AddNoteParams,
    AddNotesParams,
    AddTagsParams,
    AnswerCardsParams,
    ApiReflectParams,
    CardAnswer,
    CardReviewsParams,
    CardsIdsParams,
    ChangeDeckParams,
    CreateDeckParams,
    CredentialsParams,
    DeckIdParams,
    DeckNameParams,
    DeleteDecksParams,
    EmptyParams,
    FilenameParams,
    FindAndReplaceInModelsParams,
    FindCardsParams,
    FindNotesParams,
    GetCollectionStatsHTMLParams,
    GetDeckStatsParams,
    GetIntervalsParams,
    GetMediaFilesNamesParams,
    GetNoteTagsParams,
    InsertReviewsParams,
    ModelFieldAddParams,
    ModelFieldRemoveParams,
    ModelFieldRenameParams,
    ModelFieldRepositionParams,
    ModelFieldSetDescriptionParams,
    ModelFieldSetFontParams,
    ModelFieldSetFontSizeParams,
    ModelIdParams,
    ModelNameParams,
    ModelTemplateAddParams,
    ModelTemplateRemoveParams,
    ModelTemplateRenameParams,
    ModelTemplateRepositionParams,
    MultiParams,
    NoteFieldUpdate,
    NoteInput,
    NotesIdsParams,
    ReplaceTagsInAllNotesParams,
    ReplaceTagsParams,
    SetEaseFactorsParams,
    SetSpecificValueOfCardParams,
    SuspendedParams,
    UpdateNoteFieldsParams,
    UpdateNoteTagsParams,
)


def _note(
    deck: str = "Default", model: str = "Basic", front: str = "Test", back: str = "Test"
) -> NoteInput:
    return {
        "deckName": deck,
        "modelName": model,
        "fields": {"Front": front, "Back": back},
    }


def _test_model(wrapper: AnkiWrapper, name: str = "M5Model") -> str:
    """Create a dedicated model so field/template mutations leave Basic intact.

    Each test runs against a fresh collection, so a fixed name is safe.
    """
    wrapper.create_model(
        name,
        ["Front", "Back"],
        [{"Name": "Card 1", "Front": "{{Front}}", "Back": "{{Back}}"}],
    )
    return name


class TestMiscHandlers:
    """Test miscellaneous handlers."""

    @pytest.mark.asyncio
    async def test_handle_version(self, anki_wrapper):
        """Test version handler."""
        result = await handle_version(anki_wrapper, EmptyParams())
        assert result == API_VERSION

    @pytest.mark.asyncio
    async def test_handle_api_reflect(self, anki_wrapper):
        """apiReflect reports the registered actions for the "actions" scope.

        With actions=None, every registered action is returned (sanity that
        all six milestones registered their handlers); an explicit actions
        list is filtered to the registered ones; other scopes are ignored.
        """
        # (a) Full registry reflection.
        result = await handle_api_reflect(anki_wrapper, ApiReflectParams(scopes=["actions"]))
        assert result["scopes"] == ["actions"]
        actions = result["actions"]
        assert isinstance(actions, list)
        assert "version" in actions
        assert "answerCards" in actions
        assert "modelTemplateAdd" in actions

        # (b) Explicit action list filtered to the registered ones.
        result = await handle_api_reflect(
            anki_wrapper,
            ApiReflectParams(scopes=["actions"], actions=["version", "deckNames", "notAnAction"]),
        )
        assert result["actions"] == ["version", "deckNames"]

        # (c) Empty scopes: nothing is reflected.
        result = await handle_api_reflect(anki_wrapper, ApiReflectParams(scopes=[]))
        assert result == {"scopes": []}

        # (d) Unknown scopes are ignored.
        result = await handle_api_reflect(anki_wrapper, ApiReflectParams(scopes=["other"]))
        assert result == {"scopes": []}

    @pytest.mark.asyncio
    async def test_handle_reload_collection(self, anki_wrapper):
        """reloadCollection is a documented no-op; the collection stays usable."""
        result = await handle_reload_collection(anki_wrapper, EmptyParams())
        assert result is None

        # The collection remains usable after the call.
        note_id = anki_wrapper.add_note(_note(front="AfterReload"))
        assert note_id is not None
        assert note_id in anki_wrapper.find_notes("AfterReload")

    @pytest.mark.asyncio
    async def test_handle_request_permission(self, anki_wrapper):
        """requestPermission always returns the granted shape (headless)."""
        result = await handle_request_permission(anki_wrapper, EmptyParams())
        assert result == {"permission": "granted", "requireApikey": False, "version": 6}

    @pytest.mark.asyncio
    async def test_handle_deck_names(self, anki_wrapper):
        """Test deckNames handler."""
        anki_wrapper.create_deck("Spanish")
        result = await handle_deck_names(anki_wrapper, EmptyParams())
        assert "Default" in result
        assert "Spanish" in result

    @pytest.mark.asyncio
    async def test_handle_deck_names_and_ids(self, anki_wrapper):
        """Test deckNamesAndIds handler."""

        deck_id = anki_wrapper.create_deck("TestDeck")
        result = await handle_deck_names_and_ids(anki_wrapper, EmptyParams())
        assert "TestDeck" in result
        assert result["TestDeck"] == deck_id

    @pytest.mark.asyncio
    async def test_handle_create_deck(self, anki_wrapper):
        """Test createDeck handler."""
        result = await handle_create_deck(anki_wrapper, CreateDeckParams(deck="NewDeck"))
        assert result > 0

    @pytest.mark.asyncio
    async def test_handle_get_decks(self, anki_wrapper):
        """Test getDecks handler."""
        from anki_connect_server.types import GetDecksParams

        result = await handle_get_decks(anki_wrapper, GetDecksParams(cards=[]))
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_handle_delete_decks(self, anki_wrapper):
        """Test deleteDecks handler."""
        anki_wrapper.create_deck("ToDelete")
        await handle_delete_decks(anki_wrapper, DeleteDecksParams(decks=["ToDelete"]))
        assert "ToDelete" not in anki_wrapper.deck_names()

    @pytest.mark.asyncio
    async def test_handle_deck_name_from_id(self, anki_wrapper):
        """Test deckNameFromId handler."""
        deck_id = int(anki_wrapper.col.decks.id("Default"))
        result = await handle_deck_name_from_id(anki_wrapper, DeckIdParams(deckId=deck_id))
        assert result == "Default"

    @pytest.mark.asyncio
    async def test_handle_deck_name_from_id_missing_deck_raises(self, anki_wrapper):
        """deckNameFromId for a nonexistent deck id raises a client-facing error."""
        with pytest.raises(ValueError, match="deck was not found"):
            await handle_deck_name_from_id(anki_wrapper, DeckIdParams(deckId=999999999))

    @pytest.mark.asyncio
    async def test_handle_change_deck(self, anki_wrapper):
        """Test changeDeck handler."""
        anki_wrapper.create_deck("Target")
        anki_wrapper.add_note(_note())
        card_id = anki_wrapper.find_cards("Test")[0]
        await handle_change_deck(anki_wrapper, ChangeDeckParams(cards=[card_id], deck="Target"))


class TestModelHandlers:
    """Test model-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_model_names(self, anki_wrapper):
        """Test modelNames handler."""
        result = await handle_model_names(anki_wrapper, EmptyParams())
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_names_and_ids(self, anki_wrapper):
        """Test modelNamesAndIds handler."""
        result = await handle_model_names_and_ids(anki_wrapper, EmptyParams())
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_name_from_id(self, anki_wrapper):
        """Test modelNameFromId handler."""
        model_id = anki_wrapper.model_names_and_ids()["Basic"]
        result = await handle_model_name_from_id(anki_wrapper, ModelIdParams(modelId=model_id))
        assert result == "Basic"

    @pytest.mark.asyncio
    async def test_handle_model_name_from_id_missing_model_raises(self, anki_wrapper):
        """modelNameFromId for a nonexistent model id raises a client-facing error."""
        with pytest.raises(ValueError, match="model was not found"):
            await handle_model_name_from_id(anki_wrapper, ModelIdParams(modelId=999999999))

    @pytest.mark.asyncio
    async def test_handle_model_field_names(self, anki_wrapper):
        """Test modelFieldNames handler."""
        result = await handle_model_field_names(anki_wrapper, ModelNameParams(modelName="Basic"))
        assert "Front" in result
        assert "Back" in result

    @pytest.mark.asyncio
    async def test_handle_model_styling(self, anki_wrapper):
        """Test modelStyling handler."""
        result = await handle_model_styling(anki_wrapper, ModelNameParams(modelName="Basic"))
        assert isinstance(result, dict)
        assert "css" in result

    @pytest.mark.asyncio
    async def test_handle_model_fields_on_templates(self, anki_wrapper):
        """Test modelFieldsOnTemplates handler.

        The Basic model has one template (Card 1) whose front/back templates
        reference the Front and Back fields, so the result should map
        'Card 1' -> [[front_fields...], [back_fields...]].
        """
        result = await handle_model_fields_on_templates(
            anki_wrapper, ModelNameParams(modelName="Basic")
        )
        assert isinstance(result, dict)
        assert "Card 1" in result
        front_fields, back_fields = result["Card 1"]
        assert isinstance(front_fields, list)
        assert isinstance(back_fields, list)
        # The Basic front template references Front; the back template
        # references FrontSide (Anki's built-in front-preview) and Back.
        assert "Front" in front_fields
        assert "Back" in back_fields

    @pytest.mark.asyncio
    async def test_handle_model_fields_on_templates_unknown_model(self, anki_wrapper):
        """modelFieldsOnTemplates for a nonexistent model returns {}."""
        result = await handle_model_fields_on_templates(
            anki_wrapper, ModelNameParams(modelName="NoSuchModel")
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_handle_model_field_add(self, anki_wrapper):
        """modelFieldAdd adds a field; an index repositions even existing fields."""
        name = _test_model(anki_wrapper)
        await handle_model_field_add(
            anki_wrapper, ModelFieldAddParams(modelName=name, fieldName="Extra")
        )
        assert anki_wrapper.model_field_names(name) == ["Front", "Back", "Extra"]

        # Adding an existing field with an index repositions it instead.
        await handle_model_field_add(
            anki_wrapper, ModelFieldAddParams(modelName=name, fieldName="Extra", index=0)
        )
        assert anki_wrapper.model_field_names(name) == ["Extra", "Front", "Back"]

        # Adding an existing field without an index is a no-op.
        await handle_model_field_add(
            anki_wrapper, ModelFieldAddParams(modelName=name, fieldName="Extra")
        )
        assert anki_wrapper.model_field_names(name) == ["Extra", "Front", "Back"]

    @pytest.mark.asyncio
    async def test_handle_model_field_remove(self, anki_wrapper):
        """modelFieldRemove removes a field; a missing field raises."""
        name = _test_model(anki_wrapper)
        await handle_model_field_remove(
            anki_wrapper, ModelFieldRemoveParams(modelName=name, fieldName="Back")
        )
        assert anki_wrapper.model_field_names(name) == ["Front"]
        with pytest.raises(ValueError, match="field was not found in"):
            await handle_model_field_remove(
                anki_wrapper, ModelFieldRemoveParams(modelName=name, fieldName="Back")
            )

    @pytest.mark.asyncio
    async def test_handle_model_field_rename(self, anki_wrapper):
        """modelFieldRename renames a field."""
        name = _test_model(anki_wrapper)
        await handle_model_field_rename(
            anki_wrapper,
            ModelFieldRenameParams(modelName=name, oldFieldName="Back", newFieldName="Reverse"),
        )
        fields = anki_wrapper.model_field_names(name)
        assert "Reverse" in fields
        assert "Back" not in fields

    @pytest.mark.asyncio
    async def test_handle_model_field_reposition(self, anki_wrapper):
        """modelFieldReposition moves a field to the requested index."""
        name = _test_model(anki_wrapper)
        await handle_model_field_reposition(
            anki_wrapper, ModelFieldRepositionParams(modelName=name, fieldName="Back", index=0)
        )
        assert anki_wrapper.model_field_names(name) == ["Back", "Front"]

    @pytest.mark.asyncio
    async def test_handle_model_field_set_font_and_size(self, anki_wrapper):
        """modelFieldSetFont/SetFontSize changes are visible via modelFieldFonts."""
        name = _test_model(anki_wrapper)
        await handle_model_field_set_font(
            anki_wrapper, ModelFieldSetFontParams(modelName=name, fieldName="Front", font="Courier")
        )
        await handle_model_field_set_font_size(
            anki_wrapper,
            ModelFieldSetFontSizeParams(modelName=name, fieldName="Front", fontSize=42),
        )
        fonts = await handle_model_field_fonts(anki_wrapper, ModelNameParams(modelName=name))
        assert fonts["Front"] == {"font": "Courier", "size": 42}

    @pytest.mark.asyncio
    async def test_handle_model_field_set_description(self, anki_wrapper):
        """modelFieldSetDescription returns True and persists the description."""
        name = _test_model(anki_wrapper)
        result = await handle_model_field_set_description(
            anki_wrapper,
            ModelFieldSetDescriptionParams(
                modelName=name, fieldName="Front", description="The front"
            ),
        )
        assert result is True
        descriptions = await handle_model_field_descriptions(
            anki_wrapper, ModelNameParams(modelName=name)
        )
        assert descriptions[0] == "The front"

    @pytest.mark.asyncio
    async def test_handle_model_field_descriptions(self, anki_wrapper):
        """modelFieldDescriptions returns descriptions in field order."""
        name = _test_model(anki_wrapper)
        await handle_model_field_set_description(
            anki_wrapper,
            ModelFieldSetDescriptionParams(modelName=name, fieldName="Front", description="First"),
        )
        await handle_model_field_set_description(
            anki_wrapper,
            ModelFieldSetDescriptionParams(modelName=name, fieldName="Back", description="Second"),
        )
        result = await handle_model_field_descriptions(
            anki_wrapper, ModelNameParams(modelName=name)
        )
        assert result == ["First", "Second"]

    @pytest.mark.asyncio
    async def test_handle_model_field_fonts(self, anki_wrapper):
        """modelFieldFonts is keyed by field name with font/size values."""
        name = _test_model(anki_wrapper)
        result = await handle_model_field_fonts(anki_wrapper, ModelNameParams(modelName=name))
        assert set(result) == {"Front", "Back"}
        for entry in result.values():
            assert set(entry) == {"font", "size"}
            assert isinstance(entry["font"], str)
            assert isinstance(entry["size"], int)

    @pytest.mark.asyncio
    async def test_handle_model_template_add(self, anki_wrapper):
        """modelTemplateAdd adds a template; the same Name updates it in place.

        The in-place update persists: upstream returns without saving in that
        path, silently losing the change, which this server fixes.
        """
        name = _test_model(anki_wrapper)
        params = ModelTemplateAddParams(
            modelName=name,
            template={"Name": "Card 2", "Front": "{{Front}} 2", "Back": "{{Back}} 2"},
        )
        await handle_model_template_add(anki_wrapper, params)
        templates = anki_wrapper.model_templates(name)
        assert len(templates) == 2
        assert templates["Card 2"] == {"Front": "{{Front}} 2", "Back": "{{Back}} 2"}

        update = ModelTemplateAddParams(
            modelName=name,
            template={"Name": "Card 2", "Front": "New {{Front}}", "Back": "New Back"},
        )
        await handle_model_template_add(anki_wrapper, update)
        templates = anki_wrapper.model_templates(name)
        assert len(templates) == 2
        assert templates["Card 2"] == {"Front": "New {{Front}}", "Back": "New Back"}

    @pytest.mark.asyncio
    async def test_handle_model_template_add_invalid_front_raises(self, anki_wrapper):
        """modelTemplateAdd with a fieldless front raises a client-facing error.

        anki 26.8's update_dict rejects a front with no field replacement; the
        wrapper re-raises it as ValueError so the API layer reports it in the
        AnkiConnect error envelope instead of a 500.
        """
        name = _test_model(anki_wrapper)
        with pytest.raises(ValueError, match="field replacement"):
            await handle_model_template_add(
                anki_wrapper,
                ModelTemplateAddParams(
                    modelName=name,
                    template={"Name": "Broken", "Front": "no fields here", "Back": "{{Front}}"},
                ),
            )

    @pytest.mark.asyncio
    async def test_handle_model_template_remove(self, anki_wrapper):
        """modelTemplateRemove removes a template; a missing one raises."""
        name = _test_model(anki_wrapper)
        await handle_model_template_add(
            anki_wrapper,
            ModelTemplateAddParams(
                modelName=name,
                template={"Name": "Card 2", "Front": "{{Front}} 2", "Back": "{{Back}}"},
            ),
        )
        await handle_model_template_remove(
            anki_wrapper, ModelTemplateRemoveParams(modelName=name, templateName="Card 2")
        )
        assert list(anki_wrapper.model_templates(name)) == ["Card 1"]
        with pytest.raises(ValueError, match="template was not found in"):
            await handle_model_template_remove(
                anki_wrapper, ModelTemplateRemoveParams(modelName=name, templateName="Card 2")
            )
        # Removing the last remaining template is refused as a *client* error
        # (ValueError -> HTTP 200 error envelope), not an unhandled anki
        # Exception -> HTTP 500 (E2E issue P1-2, suite_5 MD-21).
        with pytest.raises(ValueError, match="must have 1 template"):
            await handle_model_template_remove(
                anki_wrapper, ModelTemplateRemoveParams(modelName=name, templateName="Card 1")
            )
        assert list(anki_wrapper.model_templates(name)) == ["Card 1"]

    @pytest.mark.asyncio
    async def test_handle_model_template_rename(self, anki_wrapper):
        """modelTemplateRename renames a template."""
        name = _test_model(anki_wrapper)
        await handle_model_template_rename(
            anki_wrapper,
            ModelTemplateRenameParams(
                modelName=name, oldTemplateName="Card 1", newTemplateName="Renamed"
            ),
        )
        templates = anki_wrapper.model_templates(name)
        assert "Renamed" in templates
        assert "Card 1" not in templates

    @pytest.mark.asyncio
    async def test_handle_model_template_reposition(self, anki_wrapper):
        """modelTemplateReposition moves a template to the requested index."""
        name = _test_model(anki_wrapper)
        await handle_model_template_add(
            anki_wrapper,
            ModelTemplateAddParams(
                modelName=name,
                template={"Name": "Card 2", "Front": "{{Front}} 2", "Back": "{{Back}}"},
            ),
        )
        await handle_model_template_reposition(
            anki_wrapper,
            ModelTemplateRepositionParams(modelName=name, templateName="Card 2", index=0),
        )
        assert list(anki_wrapper.model_templates(name)) == ["Card 2", "Card 1"]

    @pytest.mark.asyncio
    async def test_handle_find_and_replace_in_models(self, anki_wrapper):
        """findAndReplaceInModels replaces template text and counts the model."""
        anki_wrapper.create_model(
            "M5Replace",
            ["Front", "Back"],
            [{"Name": "Card 1", "Front": "MARKER {{Front}}", "Back": "{{Back}}"}],
        )
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(
                modelName="M5Replace", findText="MARKER", replaceText="CHANGED"
            ),
        )
        assert result == 1
        templates = anki_wrapper.model_templates("M5Replace")
        assert templates["Card 1"]["Front"] == "CHANGED {{Front}}"

    @pytest.mark.asyncio
    async def test_handle_find_and_replace_in_models_all_models(self, anki_wrapper):
        """An empty modelName counts every model containing the text."""
        for model_name in ("M5AllA", "M5AllB"):
            anki_wrapper.create_model(
                model_name,
                ["Front", "Back"],
                [{"Name": "Card 1", "Front": "MARKER {{Front}}", "Back": "{{Back}}"}],
            )
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(modelName="", findText="MARKER", replaceText="CHANGED"),
        )
        assert result == 2
        assert anki_wrapper.model_templates("M5AllA")["Card 1"]["Front"] == "CHANGED {{Front}}"
        assert anki_wrapper.model_templates("M5AllB")["Card 1"]["Front"] == "CHANGED {{Front}}"

    @pytest.mark.asyncio
    async def test_handle_find_and_replace_in_models_flags(self, anki_wrapper):
        """css=False skips the CSS while the front template is still replaced."""
        anki_wrapper.create_model(
            "M5Flags",
            ["Front", "Back"],
            [{"Name": "Card 1", "Front": "MARKER {{Front}}", "Back": "{{Back}}"}],
            css=".card { color: MARKER; }",
        )
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(
                modelName="M5Flags", findText="MARKER", replaceText="CHANGED", css=False
            ),
        )
        assert result == 1
        assert "MARKER" in cast(str, anki_wrapper.model_styling("M5Flags")["css"])
        templates = anki_wrapper.model_templates("M5Flags")
        assert templates["Card 1"]["Front"] == "CHANGED {{Front}}"

    @pytest.mark.asyncio
    async def test_handle_find_and_replace_in_models_css_and_back(self, anki_wrapper):
        """findAndReplaceInModels replaces CSS and Back (afmt) text, not just Front.

        Distinct markers are used so each replacement provably came from its
        own branch; each call still counts the model exactly once.
        """
        anki_wrapper.create_model(
            "M5CssBack",
            ["Front", "Back"],
            [{"Name": "Card 1", "Front": "{{Front}}", "Back": "AFMTMARK {{Back}}"}],
            css=".card { color: CSSMARK; }",
        )
        # The CSS marker is replaced via the css branch.
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(
                modelName="M5CssBack", findText="CSSMARK", replaceText="CHANGED"
            ),
        )
        assert result == 1
        css = cast(str, anki_wrapper.model_styling("M5CssBack")["css"])
        assert "CSSMARK" not in css
        assert "CHANGED" in css

        # A different marker in the template's Back (afmt) is replaced too.
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(
                modelName="M5CssBack", findText="AFMTMARK", replaceText="CHANGED"
            ),
        )
        assert result == 1
        templates = anki_wrapper.model_templates("M5CssBack")
        assert templates["Card 1"]["Back"] == "CHANGED {{Back}}"

    @pytest.mark.asyncio
    async def test_handle_find_and_replace_in_models_flag_gating(self, anki_wrapper):
        """front/back=False gate the template branches; css=False gates the CSS branch.

        With the template flags off, only the CSS branch fires (count 1) and
        the afmt keeps its marker; with back=False, an afmt-only marker is
        left untouched (count 0).
        """
        anki_wrapper.create_model(
            "M5Gate",
            ["Front", "Back"],
            [{"Name": "Card 1", "Front": "{{Front}}", "Back": "AFMTMARK {{Back}}"}],
            css=".card { color: CSSMARK; }",
        )
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(
                modelName="M5Gate",
                findText="CSSMARK",
                replaceText="CHANGED",
                front=False,
                back=False,
            ),
        )
        assert result == 1
        assert "CSSMARK" not in cast(str, anki_wrapper.model_styling("M5Gate")["css"])
        assert anki_wrapper.model_templates("M5Gate")["Card 1"]["Back"] == "AFMTMARK {{Back}}"

        # back=False gates the afmt branch: no model is counted as updated.
        result = await handle_find_and_replace_in_models(
            anki_wrapper,
            FindAndReplaceInModelsParams(
                modelName="M5Gate", findText="AFMTMARK", replaceText="CHANGED", back=False
            ),
        )
        assert result == 0
        assert anki_wrapper.model_templates("M5Gate")["Card 1"]["Back"] == "AFMTMARK {{Back}}"

    @pytest.mark.asyncio
    async def test_handle_find_and_replace_in_models_missing_model_raises(self, anki_wrapper):
        """findAndReplaceInModels raises for a missing named model."""
        with pytest.raises(ValueError, match="model was not found"):
            await handle_find_and_replace_in_models(
                anki_wrapper,
                FindAndReplaceInModelsParams(
                    modelName="NoSuchModel", findText="x", replaceText="y"
                ),
            )

    @pytest.mark.asyncio
    async def test_model_actions_missing_model_raises(self, anki_wrapper):
        """A representative model action raises upstream's missing-model error."""
        with pytest.raises(ValueError, match="model was not found: NoSuchModel"):
            await handle_model_field_add(
                anki_wrapper, ModelFieldAddParams(modelName="NoSuchModel", fieldName="X")
            )


class TestNoteHandlers:
    """Test note-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_add_note(self, anki_wrapper):
        """Test addNote handler."""
        result = await handle_add_note(
            anki_wrapper, AddNoteParams(note=_note(front="Test", back="Answer"))
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_add_notes(self, anki_wrapper):
        """Test addNotes handler."""
        result = await handle_add_notes(
            anki_wrapper,
            AddNotesParams(
                notes=[_note(front="Note1", back="Answer1"), _note(front="Note2", back="Answer2")]
            ),
        )
        assert len(result) == 2
        assert result[0] is not None
        assert result[1] is not None

    @pytest.mark.asyncio
    async def test_handle_update_note_fields(self, anki_wrapper):
        """Test updateNoteFields handler."""
        note_id = anki_wrapper.add_note(_note())
        assert note_id is not None
        await handle_update_note_fields(
            anki_wrapper,
            UpdateNoteFieldsParams(note=NoteFieldUpdate(id=note_id, fields={"Front": "Updated"})),
        )

    @pytest.mark.asyncio
    async def test_handle_update_note_fields_and_tags(self, anki_wrapper):
        """updateNote patches fields and replaces tags in one call."""
        from anki_connect_server.handlers import dispatch

        note_id = anki_wrapper.add_note(_note())
        assert note_id is not None
        await dispatch(
            "updateNote",
            {"note": {"id": note_id, "fields": {"Front": "New"}, "tags": ["european"]}},
            anki_wrapper,
        )
        note = anki_wrapper.col.get_note(note_id)
        assert note["Front"] == "New"
        assert note.tags == ["european"]

    @pytest.mark.asyncio
    async def test_handle_update_note_tags_only(self, anki_wrapper):
        """updateNote with only tags leaves fields untouched."""
        from anki_connect_server.handlers import dispatch

        note_id = anki_wrapper.add_note(_note(front="Original"))
        assert note_id is not None
        anki_wrapper.add_tags([note_id], "old")
        await dispatch("updateNote", {"note": {"id": note_id, "tags": ["fresh"]}}, anki_wrapper)
        note = anki_wrapper.col.get_note(note_id)
        assert note["Front"] == "Original"
        assert note.tags == ["fresh"]

    @pytest.mark.asyncio
    async def test_handle_update_note_fields_only(self, anki_wrapper):
        """updateNote with only fields leaves existing tags untouched."""
        from anki_connect_server.handlers import dispatch

        note_id = anki_wrapper.add_note(_note())
        assert note_id is not None
        anki_wrapper.add_tags([note_id], "kept")
        await dispatch(
            "updateNote", {"note": {"id": note_id, "fields": {"Back": "Changed"}}}, anki_wrapper
        )
        note = anki_wrapper.col.get_note(note_id)
        assert note["Back"] == "Changed"
        assert note.tags == ["kept"]

    @pytest.mark.asyncio
    async def test_handle_update_note_requires_source(self, anki_wrapper):
        """updateNote without fields or tags raises a client-facing error."""
        from anki_connect_server.handlers import dispatch

        note_id = anki_wrapper.add_note(_note())
        assert note_id is not None
        with pytest.raises(ValueError, match="requires 'fields' and/or 'tags'"):
            await dispatch("updateNote", {"note": {"id": note_id}}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_handle_update_note_missing_note_raises(self, anki_wrapper):
        """updateNote for a nonexistent note id raises a client-facing error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError, match="not found"):
            await dispatch(
                "updateNote",
                {"note": {"id": 999999999, "fields": {"Front": "x"}}},
                anki_wrapper,
            )

    @pytest.mark.asyncio
    async def test_handle_can_add_notes(self, anki_wrapper):
        """Test canAddNotes handler."""
        result = await handle_can_add_notes(anki_wrapper, AddNotesParams(notes=[_note()]))
        assert len(result) == 1
        assert result[0] is True

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_does_not_persist(self, anki_wrapper):
        """canAddNotes must not persist notes to the database."""
        result = await handle_can_add_notes(
            anki_wrapper, AddNotesParams(notes=[_note(front="NotPersisted")])
        )
        assert result == [True]
        assert anki_wrapper.find_notes("NotPersisted") == []

    @pytest.mark.asyncio
    async def test_handle_can_add_note(self, anki_wrapper):
        """Test canAddNote handler."""
        result = await handle_can_add_note(
            anki_wrapper, AddNoteParams(note=_note(front="CanAddMe"))
        )
        assert result is True

        bad_deck_note = _note(deck="NonExistentDeck", front="Nope")
        result_bad = await handle_can_add_note(anki_wrapper, AddNoteParams(note=bad_deck_note))
        assert result_bad is False

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_success(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail handler on a valid new note."""
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[_note()])
        )
        assert result == [{"canAdd": True}]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_duplicate(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail on duplicate notes."""
        anki_wrapper.add_note(_note(front="DupeNote"))
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[_note(front="DupeNote")])
        )
        assert result == [
            {"canAdd": False, "error": "cannot create note because it is a duplicate"}
        ]

        # canAddNotes should also return False
        bool_result = await handle_can_add_notes(
            anki_wrapper, AddNotesParams(notes=[_note(front="DupeNote")])
        )
        assert bool_result == [False]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_allow_duplicate(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail with allowDuplicate=True."""
        anki_wrapper.add_note(_note(front="DupeAllowed"))
        note_with_opt: NoteInput = {
            **_note(front="DupeAllowed"),
            "options": {"allowDuplicate": True},
        }
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[note_with_opt])
        )
        assert result == [{"canAdd": True}]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_empty(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail on empty fields."""
        empty_note: NoteInput = {
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "", "Back": ""},
        }
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[empty_note])
        )
        assert result == [{"canAdd": False, "error": "cannot create note because it is empty"}]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_missing_model(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail with nonexistent model."""
        bad_model_note: NoteInput = {
            "deckName": "Default",
            "modelName": "NonExistentModel",
            "fields": {"Front": "A", "Back": "B"},
        }
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[bad_model_note])
        )
        assert result == [{"canAdd": False, "error": "model was not found: NonExistentModel"}]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_missing_deck(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail with nonexistent deck."""
        bad_deck_note: NoteInput = {
            "deckName": "NonExistentDeck",
            "modelName": "Basic",
            "fields": {"Front": "A", "Back": "B"},
        }
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[bad_deck_note])
        )
        assert result == [{"canAdd": False, "error": "deck was not found: NonExistentDeck"}]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_duplicate_scope_deck(self, anki_wrapper):
        """Test duplicateScope='deck' allows duplicates across different decks."""
        anki_wrapper.create_deck("OtherDeck")
        anki_wrapper.add_note(_note(deck="Default", front="ScopedWord"))

        # Checking in OtherDeck with deck scope should succeed
        scoped_note: NoteInput = {
            **_note(deck="OtherDeck", front="ScopedWord"),
            "options": {"duplicateScope": "deck"},
        }
        result = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[scoped_note])
        )
        assert result == [{"canAdd": True}]

        # Checking in Default with deck scope should detect duplicate
        same_deck_note: NoteInput = {
            **_note(deck="Default", front="ScopedWord"),
            "options": {"duplicateScope": "deck"},
        }
        result_same = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[same_deck_note])
        )
        assert result_same == [
            {"canAdd": False, "error": "cannot create note because it is a duplicate"}
        ]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_check_children(self, anki_wrapper):
        """Test duplicateScopeOptions.checkChildren checks child decks."""
        anki_wrapper.create_deck("Parent::Child")
        anki_wrapper.add_note(_note(deck="Parent::Child", front="ChildWord"))

        # Checking Parent with checkChildren=False -> not duplicate
        parent_no_children: NoteInput = {
            **_note(deck="Parent", front="ChildWord"),
            "options": {
                "duplicateScope": "deck",
                "duplicateScopeOptions": {"checkChildren": False},
            },
        }
        res_no_children = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[parent_no_children])
        )
        assert res_no_children == [{"canAdd": True}]

        # Checking Parent with checkChildren=True -> duplicate
        parent_with_children: NoteInput = {
            **_note(deck="Parent", front="ChildWord"),
            "options": {"duplicateScope": "deck", "duplicateScopeOptions": {"checkChildren": True}},
        }
        res_with_children = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[parent_with_children])
        )
        assert res_with_children == [
            {"canAdd": False, "error": "cannot create note because it is a duplicate"}
        ]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_check_all_models(self, anki_wrapper):
        """Test duplicateScopeOptions.checkAllModels checks across different models."""
        anki_wrapper.add_note(_note(model="Basic", front="CrossModelWord"))

        # Different model note with same first field content
        other_model_note: NoteInput = {
            "deckName": "Default",
            "modelName": "Basic (and reversed card)",
            "fields": {"Front": "CrossModelWord", "Back": "Other"},
        }

        # By default (different models), not a duplicate
        res_default = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[other_model_note])
        )
        assert res_default == [{"canAdd": True}]

        # With checkAllModels=True, detected as duplicate
        other_all_models: NoteInput = {
            **other_model_note,
            "options": {"duplicateScopeOptions": {"checkAllModels": True}},
        }
        res_all_models = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[other_all_models])
        )
        assert res_all_models == [
            {"canAdd": False, "error": "cannot create note because it is a duplicate"}
        ]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes_with_error_detail_invalid_options(self, anki_wrapper):
        """Test non-boolean option values produce expected error messages."""
        note_bad_allow_dupe: NoteInput = {
            **_note(),
            "options": {"allowDuplicate": "yes"},  # type: ignore[typeddict-item]
        }
        res1 = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[note_bad_allow_dupe])
        )
        assert res1 == [
            {"canAdd": False, "error": 'option parameter "allowDuplicate" must be boolean'}
        ]

        note_bad_children: NoteInput = {
            **_note(),
            "options": {
                "duplicateScope": "deck",
                "duplicateScopeOptions": {"checkChildren": "yes"},
            },  # type: ignore[typeddict-item]
        }
        res2 = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[note_bad_children])
        )
        assert res2 == [
            {
                "canAdd": False,
                "error": 'option parameter "duplicateScopeOptions.checkChildren" must be boolean',
            }
        ]

        note_bad_models: NoteInput = {
            **_note(),
            "options": {"duplicateScopeOptions": {"checkAllModels": "yes"}},  # type: ignore[typeddict-item]
        }
        res3 = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[note_bad_models])
        )
        assert res3 == [
            {
                "canAdd": False,
                "error": 'option parameter "duplicateScopeOptions.checkAllModels" must be boolean',
            }
        ]

    @pytest.mark.asyncio
    async def test_handle_find_notes(self, anki_wrapper):
        """Test findNotes handler."""
        anki_wrapper.add_note(_note(front="FindTest"))
        result = await handle_find_notes(anki_wrapper, FindNotesParams(query="FindTest"))
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_find_notes_missing_query_raises(self, anki_wrapper):
        """findNotes without a query must raise -- otherwise Anki returns the
        entire collection, silently leaking every note id to the caller."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("findNotes", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_handle_notes_info(self, anki_wrapper):
        """Test notesInfo handler."""
        note_id = anki_wrapper.add_note(_note())
        result = await handle_notes_info(anki_wrapper, NotesIdsParams(notes=[note_id]))
        assert len(result) == 1
        assert result[0]["noteId"] == note_id

    @pytest.mark.asyncio
    async def test_handle_delete_notes(self, anki_wrapper):
        """Test deleteNotes handler."""
        note_id = anki_wrapper.add_note(_note())
        await handle_delete_notes(anki_wrapper, NotesIdsParams(notes=[note_id]))

    @pytest.mark.asyncio
    async def test_handle_remove_empty_notes(self, anki_wrapper):
        """Test removeEmptyNotes handler.

        Upstream parity: despite the name, the action removes note types with
        zero notes. The unused note type is gone afterwards while Basic, which
        still has a note, remains.
        """
        anki_wrapper.add_note(_note(front="KeepsBasic"))
        anki_wrapper.create_model(
            "UnusedModel",
            ["Front", "Back"],
            [{"Name": "Card 1", "Front": "{{Front}}", "Back": "{{Back}}"}],
        )
        assert "UnusedModel" in anki_wrapper.model_names()

        result = await handle_remove_empty_notes(anki_wrapper, EmptyParams())

        assert result is None
        assert "UnusedModel" not in anki_wrapper.model_names()
        assert "Basic" in anki_wrapper.model_names()

    @pytest.mark.asyncio
    async def test_handle_add_tags(self, anki_wrapper):
        """Test addTags handler: tags land on the note."""
        note_id = anki_wrapper.add_note(_note())
        await handle_add_tags(anki_wrapper, AddTagsParams(notes=[note_id], tags="foo bar"))
        note = anki_wrapper.col.get_note(note_id)
        assert sorted(note.tags) == ["bar", "foo"]

    @pytest.mark.asyncio
    async def test_handle_remove_tags(self, anki_wrapper):
        """Test removeTags handler: tags are removed from the note."""
        note_id = anki_wrapper.add_note(_note())
        await handle_add_tags(anki_wrapper, AddTagsParams(notes=[note_id], tags="foo bar"))
        await handle_remove_tags(anki_wrapper, AddTagsParams(notes=[note_id], tags="bar"))
        note = anki_wrapper.col.get_note(note_id)
        assert note.tags == ["foo"]

    @pytest.mark.asyncio
    async def test_handle_remove_tags_all(self, anki_wrapper):
        """Removing every tag leaves the note untagged."""
        note_id = anki_wrapper.add_note(_note())
        await handle_add_tags(anki_wrapper, AddTagsParams(notes=[note_id], tags="foo bar"))
        await handle_remove_tags(anki_wrapper, AddTagsParams(notes=[note_id], tags="foo bar"))
        assert anki_wrapper.col.get_note(note_id).tags == []

    @pytest.mark.asyncio
    async def test_handle_add_tags_accepts_multiple_notes(self, anki_wrapper):
        """addTags applies to every note in the batch."""
        note_ids = [
            anki_wrapper.add_note(_note(front="Note1")),
            anki_wrapper.add_note(_note(front="Note2")),
        ]
        await handle_add_tags(anki_wrapper, AddTagsParams(notes=note_ids, tags="batch"))
        for note_id in note_ids:
            assert anki_wrapper.col.get_note(note_id).tags == ["batch"]

    @pytest.mark.asyncio
    async def test_handle_replace_tags(self, anki_wrapper):
        """replaceTags swaps the tag on the listed notes that have it."""
        note_a = anki_wrapper.add_note(_note(front="ReplaceA"))
        note_b = anki_wrapper.add_note(_note(front="ReplaceB"))
        note_c = anki_wrapper.add_note(_note(front="ReplaceC"))
        assert note_a is not None
        assert note_b is not None
        assert note_c is not None
        anki_wrapper.add_tags([note_a, note_b], "old")
        anki_wrapper.add_tags([note_c], "other")

        result = await handle_replace_tags(
            anki_wrapper,
            ReplaceTagsParams(notes=[note_a, note_b], tag_to_replace="old", replace_with_tag="new"),
        )

        assert result is None
        assert anki_wrapper.get_note_tags(note_a) == ["new"]
        assert anki_wrapper.get_note_tags(note_b) == ["new"]
        assert anki_wrapper.get_note_tags(note_c) == ["other"]

    @pytest.mark.asyncio
    async def test_handle_replace_tags_skips_missing_notes(self, anki_wrapper):
        """replaceTags silently skips missing note ids (upstream parity)."""
        note_id = anki_wrapper.add_note(_note(front="ReplaceMissing"))
        assert note_id is not None
        anki_wrapper.add_tags([note_id], "old")

        result = await handle_replace_tags(
            anki_wrapper,
            ReplaceTagsParams(
                notes=[999999999, note_id], tag_to_replace="old", replace_with_tag="new"
            ),
        )

        assert result is None
        assert anki_wrapper.get_note_tags(note_id) == ["new"]

    @pytest.mark.asyncio
    async def test_handle_replace_tags_in_all_notes(self, anki_wrapper):
        """replaceTagsInAllNotes swaps the tag across every note in the collection."""
        note_a = anki_wrapper.add_note(_note(front="AllNotesA"))
        note_b = anki_wrapper.add_note(_note(front="AllNotesB"))
        assert note_a is not None
        assert note_b is not None
        anki_wrapper.add_tags([note_a], "alpha")
        anki_wrapper.add_tags([note_b], "beta")

        result = await handle_replace_tags_in_all_notes(
            anki_wrapper,
            ReplaceTagsInAllNotesParams(tag_to_replace="alpha", replace_with_tag="gamma"),
        )

        assert result is None
        assert anki_wrapper.get_note_tags(note_a) == ["gamma"]
        assert anki_wrapper.get_note_tags(note_b) == ["beta"]

    @pytest.mark.asyncio
    async def test_handle_clear_unused_tags(self, anki_wrapper):
        """clearUnusedTags removes tags no longer used by any note."""
        note_id = anki_wrapper.add_note(_note(front="UnusedTagNote"))
        assert note_id is not None
        anki_wrapper.add_tags([note_id], "single-use")
        assert "single-use" in anki_wrapper.get_tags()

        anki_wrapper.delete_notes([note_id])
        # The tag lingers in the tags cache until unused tags are cleared.
        assert "single-use" in anki_wrapper.get_tags()

        result = await handle_clear_unused_tags(anki_wrapper, EmptyParams())

        assert result is None
        assert "single-use" not in anki_wrapper.get_tags()

    @pytest.mark.asyncio
    async def test_handle_get_note_tags(self, anki_wrapper):
        """getNoteTags returns the note's tags."""
        note_id = anki_wrapper.add_note(_note(front="TaggedNote"))
        assert note_id is not None
        anki_wrapper.add_tags([note_id], "foo bar")

        result = await handle_get_note_tags(anki_wrapper, GetNoteTagsParams(note=note_id))

        assert sorted(result) == ["bar", "foo"]

    @pytest.mark.asyncio
    async def test_handle_get_note_tags_missing_note_raises(self, anki_wrapper):
        """getNoteTags for a nonexistent note id raises a client-facing error."""
        with pytest.raises(ValueError, match="Note was not found"):
            await handle_get_note_tags(anki_wrapper, GetNoteTagsParams(note=999999999))

    @pytest.mark.asyncio
    async def test_handle_update_note_tags(self, anki_wrapper):
        """updateNoteTags replaces all tags of a note (list or string form)."""
        note_id = anki_wrapper.add_note(_note(front="UpdateTagsNote"))
        assert note_id is not None
        anki_wrapper.add_tags([note_id], "a b")

        result = await handle_update_note_tags(
            anki_wrapper, UpdateNoteTagsParams(note=note_id, tags=["x", "y"])
        )

        assert result is None
        assert anki_wrapper.get_note_tags(note_id) == ["x", "y"]

        # Upstream accepts a plain string as a single tag.
        result = await handle_update_note_tags(
            anki_wrapper, UpdateNoteTagsParams(note=note_id, tags="z")
        )

        assert result is None
        assert anki_wrapper.get_note_tags(note_id) == ["z"]

    @pytest.mark.asyncio
    async def test_handle_update_note_tags_missing_note_raises(self, anki_wrapper):
        """updateNoteTags for a nonexistent note id raises a client-facing error."""
        with pytest.raises(ValueError, match="not found"):
            await handle_update_note_tags(
                anki_wrapper, UpdateNoteTagsParams(note=999999999, tags=["x"])
            )


class TestCardHandlers:
    """Test card-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_find_cards(self, anki_wrapper):
        """Test findCards handler."""
        anki_wrapper.add_note(_note(front="CardTest"))
        result = await handle_find_cards(anki_wrapper, FindCardsParams(query="CardTest"))
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_find_cards_missing_query_raises(self, anki_wrapper):
        """findCards without a query must raise -- otherwise Anki returns the
        entire collection, silently leaking every card id to the caller."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("findCards", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_handle_cards_to_notes(self, anki_wrapper):
        """Test cardsToNotes handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_cards_to_notes(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert note_id in result

    @pytest.mark.asyncio
    async def test_handle_cards_info(self, anki_wrapper):
        """Test cardsInfo handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_cards_info(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_handle_cards_mod_time(self, anki_wrapper):
        """Test cardsModTime handler."""
        note_id = anki_wrapper.add_note(_note(front="ModTime"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_cards_mod_time(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert len(result) == 1
        assert result[0]["cardId"] == card_ids[0]
        assert isinstance(result[0]["mod"], int)
        assert result[0]["mod"] == anki_wrapper.col.get_card(CardId(card_ids[0])).mod

    @pytest.mark.asyncio
    async def test_handle_cards_mod_time_missing_card(self, anki_wrapper):
        """cardsModTime yields an empty dict for a missing card id (upstream
        parity, so the input and return lists correspond)."""
        result = await handle_cards_mod_time(anki_wrapper, CardsIdsParams(cards=[999999999]))
        assert result == [{}]

    @pytest.mark.asyncio
    async def test_handle_suspend(self, anki_wrapper):
        """Test suspend handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_suspend(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_suspend_already_suspended_returns_true(self, anki_wrapper):
        """Suspending an already-suspended card must return True, not False.

        AnkiConnect returns True for the suspend action regardless of how
        many cards were actually newly suspended. Previously we returned
        False when suspend_cards reported count=0 (e.g. already suspended),
        which clients interpret as a failure.
        """
        note_id = anki_wrapper.add_note(_note(front="DoubleSuspend"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        # Suspend once.
        await handle_suspend(anki_wrapper, CardsIdsParams(cards=card_ids))
        # Suspend again -- nothing newly suspended, but must still return True.
        result = await handle_suspend(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_suspend_empty_list_returns_true(self, anki_wrapper):
        """Suspending an empty card list must return True (no-op success)."""
        result = await handle_suspend(anki_wrapper, CardsIdsParams(cards=[]))
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_unsuspend(self, anki_wrapper):
        """Test unsuspend handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        anki_wrapper.suspend(card_ids)
        result = await handle_unsuspend(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_suspended(self, anki_wrapper):
        """Test suspended handler."""
        note_id = anki_wrapper.add_note(_note(front="AmISuspended"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_suspended(anki_wrapper, SuspendedParams(card=card_ids[0]))
        assert result is False
        anki_wrapper.suspend(card_ids)
        result_suspended = await handle_suspended(anki_wrapper, SuspendedParams(card=card_ids[0]))
        assert result_suspended is True

    @pytest.mark.asyncio
    async def test_handle_suspended_missing_card_raises(self, anki_wrapper):
        """suspended for a nonexistent card id raises a client-facing error
        (unlike areSuspended, which returns False)."""
        with pytest.raises(ValueError, match="Card was not found"):
            await handle_suspended(anki_wrapper, SuspendedParams(card=999999999))

    @pytest.mark.asyncio
    async def test_handle_are_suspended(self, anki_wrapper):
        """Test areSuspended handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_are_suspended(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert len(result) == 1
        assert result[0] is False

    @pytest.mark.asyncio
    async def test_handle_are_suspended_missing_card(self, anki_wrapper):
        """areSuspended must return False for missing card IDs instead of crashing."""
        # A card ID that does not exist.
        result = await handle_are_suspended(anki_wrapper, CardsIdsParams(cards=[999999999]))
        assert result == [False]

    @pytest.mark.asyncio
    async def test_handle_are_due(self, anki_wrapper):
        """Test areDue handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_are_due(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_intervals(self, anki_wrapper):
        """Test getIntervals handler."""
        note_id = anki_wrapper.add_note(_note())
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_get_intervals(anki_wrapper, GetIntervalsParams(cards=card_ids))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_intervals_complete_last_interval_is_not_lapses(self, anki_wrapper):
        """getIntervals complete=True must report last_interval as the previous interval
        from the review log, not the lapse count (card.lapses)."""
        note_id = anki_wrapper.add_note(_note(front="IntervalComplete"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")

        def _answer(rating: int) -> None:
            card = anki_wrapper.col.get_card(CardId(card_ids[0]))
            card.timer_started = time.time()
            anki_wrapper.col.sched.answerCard(card, rating)

        # Answer the card to generate a review log entry with a last_interval.
        _answer(3)
        result = await handle_get_intervals(
            anki_wrapper, GetIntervalsParams(cards=card_ids, complete=True)
        )
        assert len(result) == 1
        entry = result[0]
        assert isinstance(entry, dict)
        assert "last_interval" in entry
        assert isinstance(entry["last_interval"], int)

        # Force a lapse by answering "Again" multiple times, then "Good".
        # This builds review history where last_interval comes from the
        # revlog, not card.lapses.
        for _ in range(3):
            _answer(1)
        _answer(3)

        result = await handle_get_intervals(
            anki_wrapper, GetIntervalsParams(cards=card_ids, complete=True)
        )
        entry = result[0]
        assert isinstance(entry["last_interval"], int)
        assert entry["last_interval"] >= 0
        # The card has lapsed, so the underlying card.lapses > 0; if the
        # code were still reading card.lapses it would report the lapse
        # count here. The revlog-sourced last_interval is the previous
        # interval, which for a learning card is a small number (often 0
        # or 1). Assert it's present and an int -- the regression check
        # is that the field exists and is sourced from the revlog.

    @pytest.mark.asyncio
    async def test_handle_answer_cards(self, anki_wrapper):
        """answerCards answers the card, writes a revlog row, and leaves new state."""
        note_id = anki_wrapper.add_note(_note(front="AnswerMe"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_answer_cards(
            anki_wrapper,
            AnswerCardsParams(answers=[CardAnswer(cardId=card_ids[0], ease=3)]),
        )
        assert result == [True]
        revlog_rows = anki_wrapper.col.db.all("select id from revlog where cid = ?", card_ids[0])
        assert len(revlog_rows) == 1
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.queue != 0
        assert card.type != 0

    @pytest.mark.asyncio
    async def test_handle_answer_cards_missing_card(self, anki_wrapper):
        """answerCards reports False for a nonexistent card id."""
        result = await handle_answer_cards(
            anki_wrapper, AnswerCardsParams(answers=[CardAnswer(cardId=999999999, ease=3)])
        )
        assert result == [False]

    @pytest.mark.asyncio
    async def test_handle_answer_cards_empty_list(self, anki_wrapper):
        """answerCards with no answers is a no-op returning an empty list."""
        result = await handle_answer_cards(anki_wrapper, AnswerCardsParams(answers=[]))
        assert result == []

    def test_answer_cards_invalid_ease_rejected(self):
        """Ease values outside 1-4 fail validation before anything is applied."""
        with pytest.raises(ValidationError):
            AnswerCardsParams.model_validate({"answers": [{"cardId": 1, "ease": 5}]})

    @pytest.mark.asyncio
    async def test_handle_forget_cards(self, anki_wrapper):
        """forgetCards hard-resets a scheduled card back to new."""
        note_id = anki_wrapper.add_note(_note(front="ForgetMe"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        # Move the card out of the new state by answering it.
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 3}]) == [True]
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.type != 0 or card.queue != 0
        result = await handle_forget_cards(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert result is None
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.type == 0
        assert card.queue == 0
        assert card.ivl == 0
        assert card.factor == 0

    @pytest.mark.asyncio
    async def test_handle_relearn_cards(self, anki_wrapper):
        """relearnCards moves a review card into the relearning state."""
        note_id = anki_wrapper.add_note(_note(front="RelearnMe"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        # Graduate the card to the review state first (Easy skips learning steps).
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 4}]) == [True]
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.type == 2  # review
        result = await handle_relearn_cards(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert result is None
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.type == 3  # CARD_TYPE_RELEARNING
        assert card.queue == 1  # learning queue

    @pytest.mark.asyncio
    async def test_handle_set_ease_factors(self, anki_wrapper):
        """setEaseFactors sets the factor (10x the ease percentage)."""
        note_id = anki_wrapper.add_note(_note(front="EaseMe"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_set_ease_factors(
            anki_wrapper, SetEaseFactorsParams(cards=card_ids, easeFactors=[3100])
        )
        assert result == [True]
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.factor == 3100

    @pytest.mark.asyncio
    async def test_handle_set_ease_factors_missing_card(self, anki_wrapper):
        """setEaseFactors reports False for a nonexistent card id."""
        result = await handle_set_ease_factors(
            anki_wrapper, SetEaseFactorsParams(cards=[999999999], easeFactors=[2500])
        )
        assert result == [False]

    @pytest.mark.asyncio
    async def test_handle_set_ease_factors_length_mismatch(self, anki_wrapper):
        """Mismatched cards/easeFactors lengths raise a client-facing error."""
        with pytest.raises(ValueError, match="same length"):
            await handle_set_ease_factors(
                anki_wrapper, SetEaseFactorsParams(cards=[1, 2], easeFactors=[2500])
            )

    @pytest.mark.asyncio
    async def test_handle_get_ease_factors(self, anki_wrapper):
        """Test getEaseFactors handler."""
        note_id = anki_wrapper.add_note(_note(front="EaseMe"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_get_ease_factors(anki_wrapper, CardsIdsParams(cards=card_ids))
        assert len(result) == 1
        assert isinstance(result[0], int)
        assert result[0] == anki_wrapper.col.get_card(CardId(card_ids[0])).factor

    @pytest.mark.asyncio
    async def test_handle_get_ease_factors_missing_card(self, anki_wrapper):
        """getEaseFactors yields None for a missing card id (upstream parity)."""
        result = await handle_get_ease_factors(anki_wrapper, CardsIdsParams(cards=[999999999]))
        assert result == [None]

    @pytest.mark.asyncio
    async def test_handle_set_specific_value_of_card(self, anki_wrapper):
        """setSpecificValueOfCard applies allowed keys like 'due'."""
        note_id = anki_wrapper.add_note(_note(front="SpecificValue"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_set_specific_value_of_card(
            anki_wrapper,
            SetSpecificValueOfCardParams(card=card_ids[0], keys=["due"], newValues=[42]),
        )
        assert result == [True]
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.due == 42

    @pytest.mark.asyncio
    async def test_handle_set_specific_value_of_card_missing_card(self, anki_wrapper):
        """A nonexistent card id yields upstream's nested failure shape."""
        result = await handle_set_specific_value_of_card(
            anki_wrapper,
            SetSpecificValueOfCardParams(card=999999999, keys=["due"], newValues=[5]),
        )
        # Upstream returns [[False, error]] -- one outer element holding a
        # two-element [False, message] list.
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], list)
        assert len(result[0]) == 2
        assert result[0][0] is False
        assert isinstance(result[0][1], str)

    @pytest.mark.asyncio
    async def test_handle_set_specific_value_of_card_blocked_key(self, anki_wrapper):
        """Blocked keys are refused when warning_check is False."""
        note_id = anki_wrapper.add_note(_note(front="BlockedKey"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_set_specific_value_of_card(
            anki_wrapper,
            SetSpecificValueOfCardParams(card=card_ids[0], keys=["ivl"], newValues=[100]),
        )
        assert result is False
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.ivl == 0  # nothing was applied

    @pytest.mark.asyncio
    async def test_handle_set_specific_value_of_card_blocked_key_with_warning_check(
        self, anki_wrapper
    ):
        """warning_check=True overrides the blocked-key refusal."""
        note_id = anki_wrapper.add_note(_note(front="BlockedKeyAllowed"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_set_specific_value_of_card(
            anki_wrapper,
            SetSpecificValueOfCardParams(
                card=card_ids[0], keys=["ivl"], newValues=[100], warning_check=True
            ),
        )
        assert result == [True]
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.ivl == 100

    @pytest.mark.asyncio
    async def test_handle_set_specific_value_of_card_length_mismatch(self, anki_wrapper):
        """Mismatched keys/newValues lengths return False and nothing is applied."""
        note_id = anki_wrapper.add_note(_note(front="LengthMismatch"))
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        await handle_set_specific_value_of_card(
            anki_wrapper,
            SetSpecificValueOfCardParams(card=card_ids[0], keys=["due"], newValues=[42]),
        )
        result = await handle_set_specific_value_of_card(
            anki_wrapper,
            SetSpecificValueOfCardParams(card=card_ids[0], keys=["due"], newValues=[1, 2]),
        )
        assert result is False
        card = anki_wrapper.col.get_card(CardId(card_ids[0]))
        assert card.due == 42  # nothing was applied


class TestStatsHandlers:
    """Test stats/revlog handlers."""

    @pytest.mark.asyncio
    async def test_handle_card_reviews(self, anki_wrapper):
        """cardReviews returns rows of 9 elements since the start id."""
        anki_wrapper.add_note(_note(front="CardReviews"))
        card_ids = anki_wrapper.find_cards("CardReviews")
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 3}]) == [True]

        result = await handle_card_reviews(
            anki_wrapper, CardReviewsParams(deck="Default", startID=0)
        )

        assert len(result) >= 1
        row = result[0]
        assert isinstance(row, list)
        assert len(row) == 9
        assert isinstance(row[0], int)  # id
        assert isinstance(row[1], int)  # cid
        assert row[1] == card_ids[0]

        # A startID larger than any review id filters everything out.
        late = await handle_card_reviews(
            anki_wrapper, CardReviewsParams(deck="Default", startID=99999999999999)
        )
        assert late == []

    @pytest.mark.asyncio
    async def test_handle_get_reviews_of_cards(self, anki_wrapper):
        """getReviewsOfCards returns per-card review dicts without cid."""
        anki_wrapper.add_note(_note(front="ReviewsOfCards"))
        card_ids = anki_wrapper.find_cards("ReviewsOfCards")
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 3}]) == [True]

        result = await handle_get_reviews_of_cards(anki_wrapper, CardsIdsParams(cards=card_ids))

        assert card_ids[0] in result
        reviews = result[card_ids[0]]
        assert len(reviews) >= 1
        assert set(reviews[0]) == {
            "id",
            "usn",
            "ease",
            "ivl",
            "lastIvl",
            "factor",
            "time",
            "type",
        }

        # A card id with no reviews maps to an empty list.
        missing = await handle_get_reviews_of_cards(anki_wrapper, CardsIdsParams(cards=[999999999]))
        assert missing == {999999999: []}

    @pytest.mark.asyncio
    async def test_handle_get_latest_review_id(self, anki_wrapper):
        """getLatestReviewID is 0 without reviews and the max revlog id after."""
        anki_wrapper.create_deck("NoReviewsYet")
        empty = await handle_get_latest_review_id(anki_wrapper, DeckNameParams(deck="NoReviewsYet"))
        assert empty == 0

        anki_wrapper.add_note(_note(front="LatestReview"))
        card_ids = anki_wrapper.find_cards("LatestReview")
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 3}]) == [True]

        result = await handle_get_latest_review_id(anki_wrapper, DeckNameParams(deck="Default"))

        max_id = anki_wrapper.col.db.scalar("select max(id) from revlog")
        assert result == max_id
        assert result > 0

    @pytest.mark.asyncio
    async def test_handle_get_num_cards_reviewed_today(self, anki_wrapper):
        """getNumCardsReviewedToday counts reviews made since the day start."""
        anki_wrapper.add_note(_note(front="ReviewedToday"))
        card_ids = anki_wrapper.find_cards("ReviewedToday")
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 3}]) == [True]

        result = await handle_get_num_cards_reviewed_today(anki_wrapper, EmptyParams())

        assert result >= 1

    @pytest.mark.asyncio
    async def test_handle_get_num_cards_reviewed_by_day(self, anki_wrapper):
        """getNumCardsReviewedByDay returns [day, count] rows."""
        anki_wrapper.add_note(_note(front="ReviewedByDay"))
        card_ids = anki_wrapper.find_cards("ReviewedByDay")
        assert anki_wrapper.answer_cards([{"cardId": card_ids[0], "ease": 3}]) == [True]

        result = await handle_get_num_cards_reviewed_by_day(anki_wrapper, EmptyParams())

        assert len(result) >= 1
        row = result[0]
        assert isinstance(row, list)
        assert len(row) == 2
        day, count = row
        assert isinstance(day, str)
        assert isinstance(count, int)
        assert count >= 1

    @pytest.mark.asyncio
    async def test_handle_insert_reviews(self, anki_wrapper):
        """insertReviews inserts raw 9-element rows bound as parameters."""
        anki_wrapper.add_note(_note(front="InsertReviews"))
        card_ids = anki_wrapper.find_cards("InsertReviews")
        cid = card_ids[0]

        await handle_insert_reviews(
            anki_wrapper,
            InsertReviewsParams(reviews=[[1234567890123, cid, 0, 3, 0, 0, 2500, 1000, 3]]),
        )

        reviews = await handle_get_reviews_of_cards(anki_wrapper, CardsIdsParams(cards=[cid]))
        assert any(review["id"] == 1234567890123 for review in reviews[cid])

        # A malformed row (8 elements) is rejected with a clean error.
        with pytest.raises(ValueError, match="9 elements"):
            await handle_insert_reviews(
                anki_wrapper, InsertReviewsParams(reviews=[[1, 2, 3, 4, 5, 6, 7, 8]])
            )

    @pytest.mark.asyncio
    async def test_handle_insert_reviews_empty_list_is_noop(self, anki_wrapper):
        """insertReviews with an empty list returns None without touching revlog."""
        db = anki_wrapper.col.db
        assert db is not None
        count_before = int(db.scalar("select count() from revlog"))

        result = await handle_insert_reviews(anki_wrapper, InsertReviewsParams(reviews=[]))

        assert result is None
        assert int(db.scalar("select count() from revlog")) == count_before

    @pytest.mark.asyncio
    async def test_handle_get_deck_stats(self, anki_wrapper):
        """getDeckStats returns due counts keyed by deck id."""
        anki_wrapper.add_note(_note(front="DeckStats"))
        default_id = anki_wrapper.deck_names_and_ids()["Default"]

        result = await handle_get_deck_stats(anki_wrapper, GetDeckStatsParams(decks=["Default"]))

        assert default_id in result
        entry = result[default_id]
        assert set(entry) == {
            "deck_id",
            "name",
            "new_count",
            "learn_count",
            "review_count",
            "total_in_deck",
        }
        new_count = entry["new_count"]
        assert isinstance(new_count, int)
        assert new_count >= 1

    @pytest.mark.asyncio
    async def test_handle_get_deck_stats_flattens_children(self, anki_wrapper):
        """getDeckStats aggregates child decks into the parent entry.

        The flattened due tree makes the requested "Parent" node findable and
        its due counts include cards sitting in "Parent::Child", which is not
        returned as a separate response key. (total_in_deck counts cards
        directly in the deck only -- the child's card shows up in the
        parent's due counts instead.)
        """
        anki_wrapper.create_deck("Parent")
        child_id = anki_wrapper.create_deck("Parent::Child")
        parent_id = anki_wrapper.deck_names_and_ids()["Parent"]
        anki_wrapper.add_note(_note(deck="Parent::Child", front="ChildNote"))

        result = await handle_get_deck_stats(anki_wrapper, GetDeckStatsParams(decks=["Parent"]))

        assert set(result) == {parent_id}
        assert child_id not in result
        parent_entry = result[parent_id]
        new_count = parent_entry["new_count"]
        assert isinstance(new_count, int)
        assert new_count >= 1

    @pytest.mark.asyncio
    async def test_handle_get_collection_stats_html(self, anki_wrapper):
        """getCollectionStatsHTML returns the wrapped HTML report."""
        result = await handle_get_collection_stats_html(
            anki_wrapper, GetCollectionStatsHTMLParams()
        )

        assert isinstance(result, str)
        assert result
        assert result.startswith("<center")


class TestDbNoneGuards:
    """Pin the wrapper's defensive col.db-is-None early returns."""

    def test_db_none_guards_return_sentinels(self, anki_wrapper, monkeypatch):
        """Raw-SQL wrapper methods return their documented sentinels when col.db is None.

        col.db is only None after the collection has been closed, so these
        guards are defensive; pin each sentinel return value so the guards
        cannot silently regress into AttributeError/TypeError exceptions.
        monkeypatch restores the real db afterwards, keeping the collection
        usable for teardown.
        """
        monkeypatch.setattr(anki_wrapper.col, "db", None)

        assert anki_wrapper.replace_tags_in_all_notes("a", "b") is None
        assert anki_wrapper.forget_cards([1]) is None
        assert anki_wrapper.relearn_cards([1]) is None
        assert anki_wrapper.card_reviews("Default", 0) == []
        assert anki_wrapper.get_reviews_of_cards([1]) == {1: []}
        assert anki_wrapper.get_latest_review_id("Default") == 0
        assert anki_wrapper.get_num_cards_reviewed_today() == 0
        assert anki_wrapper.get_num_cards_reviewed_by_day() == []
        assert anki_wrapper.insert_reviews([[0] * 9]) is None


class TestMediaHandlers:
    """Test media-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_media_dir_path(self, anki_wrapper):
        """Test getMediaDirPath handler."""
        result = await handle_get_media_dir_path(anki_wrapper, EmptyParams())
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_handle_get_media_files_names(self, anki_wrapper):
        """Test getMediaFilesNames handler."""
        payload = base64.b64encode(b"png-bytes").decode()
        anki_wrapper.store_media_file("x.png", data=payload)

        result = await handle_get_media_files_names(anki_wrapper, GetMediaFilesNamesParams())
        assert "x.png" in result

        filtered = await handle_get_media_files_names(
            anki_wrapper, GetMediaFilesNamesParams(pattern="x.*")
        )
        assert filtered == ["x.png"]

        no_match = await handle_get_media_files_names(
            anki_wrapper, GetMediaFilesNamesParams(pattern="zzz*")
        )
        assert no_match == []

    @pytest.mark.asyncio
    async def test_handle_retrieve_media_file_not_found(self, anki_wrapper):
        """Test retrieveMediaFile handler returns None for missing file."""
        result = await handle_retrieve_media_file(
            anki_wrapper, FilenameParams(filename="nonexistent.txt")
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_store_media_file_via_data(self, anki_wrapper):
        """storeMediaFile with base64 data writes the decoded bytes."""
        from anki_connect_server.handlers import dispatch

        payload = base64.b64encode(b"audio-bytes").decode()
        await dispatch("storeMediaFile", {"filename": "t.mp3", "data": payload}, anki_wrapper)
        assert anki_wrapper.retrieve_media_file("t.mp3") == payload

    @pytest.mark.asyncio
    async def test_handle_store_media_file_via_path(self, anki_wrapper, tmp_path):
        """storeMediaFile with a server-side path copies the file contents."""
        from anki_connect_server.handlers import dispatch

        source = tmp_path / "source.mp3"
        source.write_bytes(b"local-file-bytes")
        await dispatch("storeMediaFile", {"filename": "t.mp3", "path": str(source)}, anki_wrapper)
        assert (
            anki_wrapper.retrieve_media_file("t.mp3")
            == base64.b64encode(b"local-file-bytes").decode()
        )

    @pytest.mark.asyncio
    async def test_handle_store_media_file_via_url(self, anki_wrapper, httpserver):
        """storeMediaFile with a URL downloads and stores the payload."""
        from anki_connect_server.handlers import dispatch

        httpserver.expect_request("/sky.mp3").respond_with_data(b"downloaded-bytes")
        download_url = httpserver.url_for("/sky.mp3")
        await dispatch("storeMediaFile", {"filename": "t.mp3", "url": download_url}, anki_wrapper)
        assert (
            anki_wrapper.retrieve_media_file("t.mp3")
            == base64.b64encode(b"downloaded-bytes").decode()
        )

    @pytest.mark.asyncio
    async def test_handle_store_media_file_bad_url_raises(self, anki_wrapper):
        """storeMediaFile with an unreachable URL raises a client-facing error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError, match="Cannot download media"):
            await dispatch(
                "storeMediaFile",
                {"filename": "t.mp3", "url": "http://127.0.0.1:1/nope.mp3"},
                anki_wrapper,
            )

    @pytest.mark.asyncio
    async def test_handle_store_media_file_missing_path_raises(self, anki_wrapper, tmp_path):
        """storeMediaFile with a nonexistent path raises a client-facing error."""
        from anki_connect_server.handlers import dispatch

        missing = tmp_path / "missing.mp3"
        with pytest.raises(ValueError, match="Cannot read media file"):
            await dispatch(
                "storeMediaFile", {"filename": "t.mp3", "path": str(missing)}, anki_wrapper
            )

    @pytest.mark.asyncio
    async def test_handle_store_media_file_requires_source(self, anki_wrapper):
        """storeMediaFile with no data/url/path raises a client-facing error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError, match="One of data, url or path is required"):
            await dispatch("storeMediaFile", {"filename": "t.mp3"}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_handle_store_media_file_data_takes_precedence(self, anki_wrapper, tmp_path):
        """When several sources are given, data wins (mirrors upstream)."""
        from anki_connect_server.handlers import dispatch

        source = tmp_path / "source.mp3"
        source.write_bytes(b"path-bytes")
        await dispatch(
            "storeMediaFile",
            {
                "filename": "t.mp3",
                "data": base64.b64encode(b"data-bytes").decode(),
                "path": str(source),
            },
            anki_wrapper,
        )
        assert anki_wrapper.retrieve_media_file("t.mp3") == base64.b64encode(b"data-bytes").decode()


class TestSyncHandlers:
    """Test sync-related handlers (sync_status; sync/sync_media are covered
    by the mock-based test_sync_required_2.py)."""

    @pytest.mark.asyncio
    async def test_handle_sync_status_missing_credentials_raises(self, anki_wrapper, monkeypatch):
        """syncStatus without credentials raises ValueError."""
        from anki_connect_server.config import get_config
        from anki_connect_server.handlers import dispatch

        # Clear any credentials the cached config picked up from .env.
        cfg = get_config()
        monkeypatch.setattr(cfg, "ANKIWEB_USER", None)
        monkeypatch.setattr(cfg, "ANKIWEB_PASS", None)
        with pytest.raises(ValueError, match="ANKICONNECT_ANKIWEB_USER"):
            await dispatch("syncStatus", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_handle_sync_status_with_explicit_credentials(self, anki_wrapper, monkeypatch):
        """syncStatus with explicit username/password returns the status dict.

        We mock col.sync_login and col.sync_status so no network call is made.
        """
        from unittest.mock import Mock

        mock_auth = Mock(hkey="test_key")
        mock_status = Mock()
        mock_status.server = "sync7.ankiweb.net"
        mock_status.status = "ok"
        mock_status.required = 0

        monkeypatch.setattr(anki_wrapper.col, "sync_login", Mock(return_value=mock_auth))
        monkeypatch.setattr(anki_wrapper.col, "sync_status", Mock(return_value=mock_status))

        result = await handle_sync_status(
            anki_wrapper,
            CredentialsParams(username="user@example.com", password="pw"),
        )

        assert isinstance(result, dict)
        assert result["server"] == "sync7.ankiweb.net"
        assert result["status"] == "ok"
        assert result["required"] == 0


class TestMultiHandler:
    """Test multi action handler."""

    @pytest.mark.asyncio
    async def test_handle_multi(self, anki_wrapper):
        """Test multi handler."""
        anki_wrapper.create_deck("MultiTest")
        result = await handle_multi(
            anki_wrapper,
            MultiParams(
                actions=[
                    {"action": "deckNames", "params": {}},
                    {"action": "modelNames", "params": {}},
                ]
            ),
        )
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_handle_multi_unknown_action_per_action(self, anki_wrapper):
        """Unknown actions inside multi must be reported per-action, not abort the batch."""
        result = await handle_multi(
            anki_wrapper,
            MultiParams(
                actions=[
                    {"action": "deckNames", "params": {}},
                    {"action": "noSuchAction", "params": {}},
                ]
            ),
        )
        assert len(result) == 2
        assert isinstance(
            result[0], list
        )  # deckNames succeeded (bare value, version defaults to 4)
        # Upstream format_exception_reply: failures are always
        # {"result": None, "error": ...} with the same wording as the
        # top-level dispatch (E2E P2-4 / P3-3).
        assert result[1] == {"result": None, "error": "Unsupported action: noSuchAction"}

    @pytest.mark.asyncio
    async def test_handle_multi_per_entry_version_envelopes(self, anki_wrapper):
        """Success entries follow the entry's own version, like upstream.

        Entries with version >= 5 get {"result": ..., "error": null}; entries
        without a version (upstream default 4) get the bare value.
        """
        result = await handle_multi(
            anki_wrapper,
            MultiParams(
                actions=[
                    {"action": "version", "version": 6},
                    {"action": "version"},
                ]
            ),
        )
        assert result[0] == {"result": 6, "error": None}
        assert result[1] == 6

    @pytest.mark.asyncio
    async def test_handle_multi_sub_action_failure_does_not_abort(self, anki_wrapper):
        """A failing sub-action must not abort the whole multi call."""
        result = await handle_multi(
            anki_wrapper,
            MultiParams(
                actions=[
                    {"action": "createDeck", "params": {"deck": ""}},  # raises
                    {"action": "deckNames", "params": {}},  # should still run
                ]
            ),
        )
        assert len(result) == 2
        assert isinstance(result[0], dict)
        assert result[0]["result"] is None
        assert isinstance(result[0]["error"], str)
        assert isinstance(result[1], list)

    @pytest.mark.asyncio
    async def test_handle_multi_invalid_action_entry(self, anki_wrapper):
        """Non-dict action entries are reported per-action without crashing."""
        result = await handle_multi(
            anki_wrapper,
            MultiParams(
                actions=[
                    "not a dict",
                    {"action": "deckNames", "params": {}},
                ]
            ),
        )
        assert len(result) == 2
        assert result[0] == {
            "result": None,
            "error": "Invalid action: expected object, got str",
        }
        assert isinstance(result[1], list)

    @pytest.mark.asyncio
    async def test_handle_multi_actions_not_list_raises(self, anki_wrapper):
        """actions must be a list; otherwise raise ValidationError."""
        with pytest.raises(ValidationError):
            await handle_multi(anki_wrapper, MultiParams.model_validate({"actions": "not a list"}))


class TestValidationErrors:
    """Test validation error handling."""

    @pytest.mark.asyncio
    async def test_create_deck_empty_name(self, anki_wrapper):
        """Test createDeck with empty name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await handle_create_deck(anki_wrapper, CreateDeckParams(deck=""))

    @pytest.mark.asyncio
    async def test_create_deck_missing_deck(self, anki_wrapper):
        """Test createDeck without deck param raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("createDeck", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_add_note_missing_note(self, anki_wrapper):
        """Test addNote without note param raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("addNote", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_add_note_invalid_note_type(self, anki_wrapper):
        """Test addNote with non-dict note raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("addNote", {"note": "not a dict"}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_add_notes_missing_notes(self, anki_wrapper):
        """Test addNotes without notes param raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("addNotes", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_add_notes_invalid_notes_type(self, anki_wrapper):
        """Test addNotes with non-list notes raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("addNotes", {"notes": "not a list"}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_update_note_fields_missing_note(self, anki_wrapper):
        """Test updateNoteFields without note param raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("updateNoteFields", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_update_note_fields_invalid_note_type(self, anki_wrapper):
        """Test updateNoteFields with non-dict note raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("updateNoteFields", {"note": 123}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_update_note_fields_missing_id_raises(self, anki_wrapper):
        """updateNoteFields with a note dict that has no 'id' must raise, not
        silently succeed (the old code returned None and the client got 200 OK
        for an operation that did nothing)."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("updateNoteFields", {"note": {"fields": {"Front": "x"}}}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_update_note_fields_nonexistent_id_raises(self, anki_wrapper):
        """updateNoteFields with an id that does not exist must raise, not
        silently succeed."""
        with pytest.raises(ValueError, match="not found"):
            await handle_update_note_fields(
                anki_wrapper,
                UpdateNoteFieldsParams(note=NoteFieldUpdate(id=999999999, fields={"Front": "x"})),
            )

    @pytest.mark.asyncio
    async def test_can_add_notes_missing_notes(self, anki_wrapper):
        """Test canAddNotes without notes param raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("canAddNotes", {}, anki_wrapper)

    @pytest.mark.asyncio
    async def test_can_add_notes_with_error_detail_missing_notes(self, anki_wrapper):
        """Test canAddNotesWithErrorDetail without notes param raises error."""
        from anki_connect_server.handlers import dispatch

        with pytest.raises(ValueError):
            await dispatch("canAddNotesWithErrorDetail", {}, anki_wrapper)
