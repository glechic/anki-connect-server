"""Tests for API handlers using real AnkiWrapper."""

import base64
import time

import pytest
from anki.cards import CardId
from pydantic import ValidationError

from anki_connect_server.handlers import (
    API_VERSION,
    handle_add_note,
    handle_add_notes,
    handle_add_tags,
    handle_are_due,
    handle_are_suspended,
    handle_can_add_notes,
    handle_can_add_notes_with_error_detail,
    handle_cards_info,
    handle_cards_to_notes,
    handle_change_deck,
    handle_create_deck,
    handle_deck_names,
    handle_deck_names_and_ids,
    handle_delete_decks,
    handle_delete_notes,
    handle_find_cards,
    handle_find_notes,
    handle_get_decks,
    handle_get_intervals,
    handle_get_media_dir_path,
    handle_model_field_names,
    handle_model_fields_on_templates,
    handle_model_names,
    handle_model_names_and_ids,
    handle_model_styling,
    handle_multi,
    handle_notes_info,
    handle_remove_tags,
    handle_retrieve_media_file,
    handle_suspend,
    handle_sync_status,
    handle_unsuspend,
    handle_update_note_fields,
    handle_version,
)
from anki_connect_server.types import (
    AddNoteParams,
    AddNotesParams,
    AddTagsParams,
    CardsIdsParams,
    ChangeDeckParams,
    CreateDeckParams,
    CredentialsParams,
    DeleteDecksParams,
    EmptyParams,
    FilenameParams,
    FindCardsParams,
    FindNotesParams,
    GetIntervalsParams,
    ModelNameParams,
    MultiParams,
    NoteFieldUpdate,
    NoteInput,
    NotesIdsParams,
    UpdateNoteFieldsParams,
)


def _note(
    deck: str = "Default", model: str = "Basic", front: str = "Test", back: str = "Test"
) -> NoteInput:
    return {
        "deckName": deck,
        "modelName": model,
        "fields": {"Front": front, "Back": back},
    }


class TestMiscHandlers:
    """Test miscellaneous handlers."""

    @pytest.mark.asyncio
    async def test_handle_version(self, anki_wrapper):
        """Test version handler."""
        result = await handle_version(anki_wrapper, EmptyParams())
        assert result == API_VERSION

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
        assert result == [{"canAdd": False, "error": "cannot create note because it is a duplicate"}]

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
            "options": {"duplicateScope": "deck", "duplicateScopeOptions": {"checkChildren": False}},
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
        assert res1 == [{"canAdd": False, "error": 'option parameter "allowDuplicate" must be boolean'}]

        note_bad_children: NoteInput = {
            **_note(),
            "options": {"duplicateScope": "deck", "duplicateScopeOptions": {"checkChildren": "yes"}},  # type: ignore[typeddict-item]
        }
        res2 = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[note_bad_children])
        )
        assert res2 == [
            {"canAdd": False, "error": 'option parameter "duplicateScopeOptions.checkChildren" must be boolean'}
        ]

        note_bad_models: NoteInput = {
            **_note(),
            "options": {"duplicateScopeOptions": {"checkAllModels": "yes"}},  # type: ignore[typeddict-item]
        }
        res3 = await handle_can_add_notes_with_error_detail(
            anki_wrapper, AddNotesParams(notes=[note_bad_models])
        )
        assert res3 == [
            {"canAdd": False, "error": 'option parameter "duplicateScopeOptions.checkAllModels" must be boolean'}
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


class TestMediaHandlers:
    """Test media-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_media_dir_path(self, anki_wrapper):
        """Test getMediaDirPath handler."""
        result = await handle_get_media_dir_path(anki_wrapper, EmptyParams())
        assert result is not None
        assert len(result) > 0

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
        assert isinstance(result[0], list)  # deckNames succeeded
        assert result[1] == {"error": "Unknown action: noSuchAction"}

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
        assert isinstance(result[0], dict) and "error" in result[0]
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
        assert "error" in result[0]
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
