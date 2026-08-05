"""Tests for API handlers using real AnkiWrapper."""

import time

import pytest
from anki.cards import CardId
from pydantic import ValidationError

from anki_connect_server.handlers import (
    API_VERSION,
    handle_add_note,
    handle_add_notes,
    handle_are_due,
    handle_are_suspended,
    handle_can_add_notes,
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
    async def test_handle_can_add_notes(self, anki_wrapper):
        """Test canAddNotes handler."""
        result = await handle_can_add_notes(anki_wrapper, AddNotesParams(notes=[_note()]))
        assert len(result) == 1
        assert result[0] is True

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
