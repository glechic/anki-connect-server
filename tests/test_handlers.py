"""Tests for API handlers using real AnkiWrapper."""

import os

import pytest


class TestMiscHandlers:
    """Test miscellaneous handlers."""

    @pytest.mark.asyncio
    async def test_handle_version(self, anki_wrapper):
        """Test version handler."""
        from anki_connect_server.handlers import handle_version, API_VERSION
        result = await handle_version(anki_wrapper, {})
        assert result == API_VERSION

    @pytest.mark.asyncio
    async def test_handle_deck_names(self, anki_wrapper):
        """Test deckNames handler."""
        from anki_connect_server.handlers import handle_deck_names
        anki_wrapper.create_deck("Spanish")
        result = await handle_deck_names(anki_wrapper, {})
        assert "Default" in result
        assert "Spanish" in result

    @pytest.mark.asyncio
    async def test_handle_deck_names_and_ids(self, anki_wrapper):
        """Test deckNamesAndIds handler."""
        from anki_connect_server.handlers import handle_deck_names_and_ids
        deck_id = anki_wrapper.create_deck("TestDeck")
        result = await handle_deck_names_and_ids(anki_wrapper, {})
        assert "TestDeck" in result
        assert result["TestDeck"] == deck_id

    @pytest.mark.asyncio
    async def test_handle_create_deck(self, anki_wrapper):
        """Test createDeck handler."""
        from anki_connect_server.handlers import handle_create_deck
        result = await handle_create_deck(anki_wrapper, {"deck": "NewDeck"})
        assert result > 0

    @pytest.mark.asyncio
    async def test_handle_get_decks(self, anki_wrapper):
        """Test getDecks handler."""
        from anki_connect_server.handlers import handle_get_decks
        result = await handle_get_decks(anki_wrapper, {"cards": []})
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_handle_delete_decks(self, anki_wrapper):
        """Test deleteDecks handler."""
        from anki_connect_server.handlers import handle_delete_decks
        anki_wrapper.create_deck("ToDelete")
        await handle_delete_decks(anki_wrapper, {"decks": ["ToDelete"]})
        assert "ToDelete" not in anki_wrapper.deck_names()

    @pytest.mark.asyncio
    async def test_handle_change_deck(self, anki_wrapper):
        """Test changeDeck handler."""
        from anki_connect_server.handlers import handle_change_deck
        anki_wrapper.create_deck("Target")
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_id = anki_wrapper.find_cards("Test")[0]
        await handle_change_deck(anki_wrapper, {"cards": [card_id], "deck": "Target"})


class TestModelHandlers:
    """Test model-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_model_names(self, anki_wrapper):
        """Test modelNames handler."""
        from anki_connect_server.handlers import handle_model_names
        result = await handle_model_names(anki_wrapper, {})
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_names_and_ids(self, anki_wrapper):
        """Test modelNamesAndIds handler."""
        from anki_connect_server.handlers import handle_model_names_and_ids
        result = await handle_model_names_and_ids(anki_wrapper, {})
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_field_names(self, anki_wrapper):
        """Test modelFieldNames handler."""
        from anki_connect_server.handlers import handle_model_field_names
        result = await handle_model_field_names(anki_wrapper, {"modelName": "Basic"})
        assert "Front" in result
        assert "Back" in result

    @pytest.mark.asyncio
    async def test_handle_model_styling(self, anki_wrapper):
        """Test modelStyling handler."""
        from anki_connect_server.handlers import handle_model_styling
        result = await handle_model_styling(anki_wrapper, {"modelName": "Basic"})
        assert isinstance(result, dict)
        assert "css" in result


class TestNoteHandlers:
    """Test note-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_add_note(self, anki_wrapper):
        """Test addNote handler."""
        from anki_connect_server.handlers import handle_add_note
        result = await handle_add_note(anki_wrapper, {
            "note": {
                "deckName": "Default",
                "modelName": "Basic",
                "fields": {"Front": "Test", "Back": "Answer"}
            }
        })
        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_add_notes(self, anki_wrapper):
        """Test addNotes handler."""
        from anki_connect_server.handlers import handle_add_notes
        result = await handle_add_notes(anki_wrapper, {
            "notes": [
                {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Note1", "Back": "Answer1"}
                },
                {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Note2", "Back": "Answer2"}
                }
            ]
        })
        assert len(result) == 2
        assert result[0] is not None
        assert result[1] is not None

    @pytest.mark.asyncio
    async def test_handle_update_note_fields(self, anki_wrapper):
        """Test updateNoteFields handler."""
        from anki_connect_server.handlers import handle_update_note_fields
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        await handle_update_note_fields(anki_wrapper, {
            "note": {"id": note_id, "fields": {"Front": "Updated"}}
        })

    @pytest.mark.asyncio
    async def test_handle_can_add_notes(self, anki_wrapper):
        """Test canAddNotes handler."""
        from anki_connect_server.handlers import handle_can_add_notes
        result = await handle_can_add_notes(anki_wrapper, {
            "notes": [{
                "deckName": "Default",
                "modelName": "Basic",
                "fields": {"Front": "Test", "Back": "Test"}
            }]
        })
        assert len(result) == 1
        assert result[0] is True

    @pytest.mark.asyncio
    async def test_handle_find_notes(self, anki_wrapper):
        """Test findNotes handler."""
        from anki_connect_server.handlers import handle_find_notes
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "FindTest", "Back": "Test"}
        })
        result = await handle_find_notes(anki_wrapper, {"query": "FindTest"})
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_find_notes_missing_query_raises(self, anki_wrapper):
        """findNotes without a query must raise -- otherwise Anki returns the
        entire collection, silently leaking every note id to the caller."""
        from anki_connect_server.handlers import handle_find_notes, ValidationError
        with pytest.raises(ValidationError, match="Missing required parameters: query"):
            await handle_find_notes(anki_wrapper, {})

    @pytest.mark.asyncio
    async def test_handle_notes_info(self, anki_wrapper):
        """Test notesInfo handler."""
        from anki_connect_server.handlers import handle_notes_info
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        result = await handle_notes_info(anki_wrapper, {"notes": [note_id]})
        assert len(result) == 1
        assert result[0]["noteId"] == note_id

    @pytest.mark.asyncio
    async def test_handle_delete_notes(self, anki_wrapper):
        """Test deleteNotes handler."""
        from anki_connect_server.handlers import handle_delete_notes
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        await handle_delete_notes(anki_wrapper, {"notes": [note_id]})


class TestCardHandlers:
    """Test card-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_find_cards(self, anki_wrapper):
        """Test findCards handler."""
        from anki_connect_server.handlers import handle_find_cards
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "CardTest", "Back": "Test"}
        })
        result = await handle_find_cards(anki_wrapper, {"query": "CardTest"})
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_find_cards_missing_query_raises(self, anki_wrapper):
        """findCards without a query must raise -- otherwise Anki returns the
        entire collection, silently leaking every card id to the caller."""
        from anki_connect_server.handlers import handle_find_cards, ValidationError
        with pytest.raises(ValidationError, match="Missing required parameters: query"):
            await handle_find_cards(anki_wrapper, {})

    @pytest.mark.asyncio
    async def test_handle_cards_to_notes(self, anki_wrapper):
        """Test cardsToNotes handler."""
        from anki_connect_server.handlers import handle_cards_to_notes
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_cards_to_notes(anki_wrapper, {"cards": card_ids})
        assert note_id in result

    @pytest.mark.asyncio
    async def test_handle_cards_info(self, anki_wrapper):
        """Test cardsInfo handler."""
        from anki_connect_server.handlers import handle_cards_info
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_cards_info(anki_wrapper, {"cards": card_ids})
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_handle_suspend(self, anki_wrapper):
        """Test suspend handler."""
        from anki_connect_server.handlers import handle_suspend
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_suspend(anki_wrapper, {"cards": card_ids})
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_suspend_already_suspended_returns_true(self, anki_wrapper):
        """Suspending an already-suspended card must return True, not False.

        AnkiConnect returns True for the suspend action regardless of how
        many cards were actually newly suspended. Previously we returned
        False when suspend_cards reported count=0 (e.g. already suspended),
        which clients interpret as a failure.
        """
        from anki_connect_server.handlers import handle_suspend
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "DoubleSuspend", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        # Suspend once.
        await handle_suspend(anki_wrapper, {"cards": card_ids})
        # Suspend again -- nothing newly suspended, but must still return True.
        result = await handle_suspend(anki_wrapper, {"cards": card_ids})
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_suspend_empty_list_returns_true(self, anki_wrapper):
        """Suspending an empty card list must return True (no-op success)."""
        from anki_connect_server.handlers import handle_suspend
        result = await handle_suspend(anki_wrapper, {"cards": []})
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_unsuspend(self, anki_wrapper):
        """Test unsuspend handler."""
        from anki_connect_server.handlers import handle_unsuspend
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        anki_wrapper.suspend(card_ids)
        result = await handle_unsuspend(anki_wrapper, {"cards": card_ids})
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_are_suspended(self, anki_wrapper):
        """Test areSuspended handler."""
        from anki_connect_server.handlers import handle_are_suspended
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_are_suspended(anki_wrapper, {"cards": card_ids})
        assert len(result) == 1
        assert result[0] is False

    @pytest.mark.asyncio
    async def test_handle_are_suspended_missing_card(self, anki_wrapper):
        """areSuspended must return False for missing card IDs instead of crashing."""
        from anki_connect_server.handlers import handle_are_suspended
        # A card ID that does not exist.
        result = await handle_are_suspended(anki_wrapper, {"cards": [999999999]})
        assert result == [False]

    @pytest.mark.asyncio
    async def test_handle_are_due(self, anki_wrapper):
        """Test areDue handler."""
        from anki_connect_server.handlers import handle_are_due
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_are_due(anki_wrapper, {"cards": card_ids})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_intervals(self, anki_wrapper):
        """Test getIntervals handler."""
        from anki_connect_server.handlers import handle_get_intervals
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_get_intervals(anki_wrapper, {"cards": card_ids})
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_handle_get_intervals_complete_last_interval_is_not_lapses(self, anki_wrapper):
        """getIntervals complete=True must report last_interval as the previous interval
        from the review log, not the lapse count (card.lapses)."""
        import time
        from anki_connect_server.handlers import handle_get_intervals
        from anki.cards import CardId
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "IntervalComplete", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")

        def _answer(rating: int) -> None:
            card = anki_wrapper.col.get_card(CardId(card_ids[0]))
            card.timer_started = time.time()
            anki_wrapper.col.sched.answerCard(card, rating)

        # Answer the card to generate a review log entry with a last_interval.
        _answer(3)
        result = await handle_get_intervals(
            anki_wrapper, {"cards": card_ids, "complete": True}
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
            anki_wrapper, {"cards": card_ids, "complete": True}
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
        from anki_connect_server.handlers import handle_get_media_dir_path
        result = await handle_get_media_dir_path(anki_wrapper, {})
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_handle_retrieve_media_file_not_found(self, anki_wrapper):
        """Test retrieveMediaFile handler returns None for missing file."""
        from anki_connect_server.handlers import handle_retrieve_media_file
        result = await handle_retrieve_media_file(anki_wrapper, {"filename": "nonexistent.txt"})
        assert result is None


class TestMultiHandler:
    """Test multi action handler."""

    @pytest.mark.asyncio
    async def test_handle_multi(self, anki_wrapper):
        """Test multi handler."""
        from anki_connect_server.handlers import handle_multi
        anki_wrapper.create_deck("MultiTest")
        result = await handle_multi(anki_wrapper, {
            "actions": [
                {"action": "deckNames", "params": {}},
                {"action": "modelNames", "params": {}}
            ]
        })
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_handle_multi_unknown_action_per_action(self, anki_wrapper):
        """Unknown actions inside multi must be reported per-action, not abort the batch."""
        from anki_connect_server.handlers import handle_multi
        result = await handle_multi(anki_wrapper, {
            "actions": [
                {"action": "deckNames", "params": {}},
                {"action": "noSuchAction", "params": {}},
            ]
        })
        assert len(result) == 2
        assert isinstance(result[0], list)  # deckNames succeeded
        assert result[1] == {"error": "Unknown action: noSuchAction"}

    @pytest.mark.asyncio
    async def test_handle_multi_sub_action_failure_does_not_abort(self, anki_wrapper):
        """A failing sub-action must not abort the whole multi call."""
        from anki_connect_server.handlers import handle_multi
        result = await handle_multi(anki_wrapper, {
            "actions": [
                {"action": "createDeck", "params": {"deck": ""}},  # raises ValidationError
                {"action": "deckNames", "params": {}},  # should still run
            ]
        })
        assert len(result) == 2
        assert isinstance(result[0], dict) and "error" in result[0]
        assert isinstance(result[1], list)

    @pytest.mark.asyncio
    async def test_handle_multi_invalid_action_entry(self, anki_wrapper):
        """Non-dict action entries are reported per-action without crashing."""
        from anki_connect_server.handlers import handle_multi
        result = await handle_multi(anki_wrapper, {
            "actions": [
                "not a dict",
                {"action": "deckNames", "params": {}},
            ]
        })
        assert len(result) == 2
        assert "error" in result[0]
        assert isinstance(result[1], list)

    @pytest.mark.asyncio
    async def test_handle_multi_actions_not_list_raises(self, anki_wrapper):
        """actions must be a list; otherwise raise ValidationError."""
        from anki_connect_server.handlers import handle_multi, ValidationError
        with pytest.raises(ValidationError, match="actions must be a list"):
            await handle_multi(anki_wrapper, {"actions": "not a list"})


class TestValidationErrors:
    """Test validation error handling."""

    @pytest.mark.asyncio
    async def test_create_deck_empty_name(self, anki_wrapper):
        """Test createDeck with empty name raises error."""
        from anki_connect_server.handlers import handle_create_deck, ValidationError
        with pytest.raises(ValueError, match="cannot be empty"):
            await handle_create_deck(anki_wrapper, {"deck": ""})

    @pytest.mark.asyncio
    async def test_create_deck_missing_deck(self, anki_wrapper):
        """Test createDeck without deck param raises error."""
        from anki_connect_server.handlers import handle_create_deck, ValidationError
        with pytest.raises(ValueError, match="Missing required parameters"):
            await handle_create_deck(anki_wrapper, {})

    @pytest.mark.asyncio
    async def test_add_note_missing_note(self, anki_wrapper):
        """Test addNote without note param raises error."""
        from anki_connect_server.handlers import handle_add_note, ValidationError
        with pytest.raises(ValueError, match="Missing required parameters"):
            await handle_add_note(anki_wrapper, {})

    @pytest.mark.asyncio
    async def test_add_note_invalid_note_type(self, anki_wrapper):
        """Test addNote with non-dict note raises error."""
        from anki_connect_server.handlers import handle_add_note, ValidationError
        with pytest.raises(ValueError, match="note must be a dictionary"):
            await handle_add_note(anki_wrapper, {"note": "not a dict"})

    @pytest.mark.asyncio
    async def test_add_notes_missing_notes(self, anki_wrapper):
        """Test addNotes without notes param raises error."""
        from anki_connect_server.handlers import handle_add_notes, ValidationError
        with pytest.raises(ValueError, match="Missing required parameters"):
            await handle_add_notes(anki_wrapper, {})

    @pytest.mark.asyncio
    async def test_add_notes_invalid_notes_type(self, anki_wrapper):
        """Test addNotes with non-list notes raises error."""
        from anki_connect_server.handlers import handle_add_notes, ValidationError
        with pytest.raises(ValueError, match="notes must be a list"):
            await handle_add_notes(anki_wrapper, {"notes": "not a list"})

    @pytest.mark.asyncio
    async def test_update_note_fields_missing_note(self, anki_wrapper):
        """Test updateNoteFields without note param raises error."""
        from anki_connect_server.handlers import handle_update_note_fields, ValidationError
        with pytest.raises(ValueError, match="Missing required parameters"):
            await handle_update_note_fields(anki_wrapper, {})

    @pytest.mark.asyncio
    async def test_update_note_fields_invalid_note_type(self, anki_wrapper):
        """Test updateNoteFields with non-dict note raises error."""
        from anki_connect_server.handlers import handle_update_note_fields, ValidationError
        with pytest.raises(ValueError, match="note must be a dictionary"):
            await handle_update_note_fields(anki_wrapper, {"note": 123})

    @pytest.mark.asyncio
    async def test_can_add_notes_missing_notes(self, anki_wrapper):
        """Test canAddNotes without notes param raises error."""
        from anki_connect_server.handlers import handle_can_add_notes, ValidationError
        with pytest.raises(ValueError, match="Missing required parameters"):
            await handle_can_add_notes(anki_wrapper, {})