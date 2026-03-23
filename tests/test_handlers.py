"""Tests for API handlers using real AnkiWrapper."""

import os

import pytest


class TestMiscHandlers:
    """Test miscellaneous handlers."""

    @pytest.mark.asyncio
    async def test_handle_version(self, anki_wrapper):
        """Test version handler."""
        from api.handlers import handle_version, API_VERSION
        result = await handle_version(anki_wrapper, {})
        assert result == API_VERSION

    @pytest.mark.asyncio
    async def test_handle_deck_names(self, anki_wrapper):
        """Test deckNames handler."""
        from api.handlers import handle_deck_names
        anki_wrapper.create_deck("Spanish")
        result = await handle_deck_names(anki_wrapper, {})
        assert "Default" in result
        assert "Spanish" in result

    @pytest.mark.asyncio
    async def test_handle_deck_names_and_ids(self, anki_wrapper):
        """Test deckNamesAndIds handler."""
        from api.handlers import handle_deck_names_and_ids
        deck_id = anki_wrapper.create_deck("TestDeck")
        result = await handle_deck_names_and_ids(anki_wrapper, {})
        assert "TestDeck" in result
        assert result["TestDeck"] == deck_id

    @pytest.mark.asyncio
    async def test_handle_create_deck(self, anki_wrapper):
        """Test createDeck handler."""
        from api.handlers import handle_create_deck
        result = await handle_create_deck(anki_wrapper, {"deck": "NewDeck"})
        assert result > 0

    @pytest.mark.asyncio
    async def test_handle_get_decks(self, anki_wrapper):
        """Test getDecks handler."""
        from api.handlers import handle_get_decks
        result = await handle_get_decks(anki_wrapper, {"cards": []})
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_handle_delete_decks(self, anki_wrapper):
        """Test deleteDecks handler."""
        from api.handlers import handle_delete_decks
        anki_wrapper.create_deck("ToDelete")
        await handle_delete_decks(anki_wrapper, {"decks": ["ToDelete"]})
        assert "ToDelete" not in anki_wrapper.deck_names()

    @pytest.mark.asyncio
    async def test_handle_change_deck(self, anki_wrapper):
        """Test changeDeck handler."""
        from api.handlers import handle_change_deck
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
        from api.handlers import handle_model_names
        result = await handle_model_names(anki_wrapper, {})
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_names_and_ids(self, anki_wrapper):
        """Test modelNamesAndIds handler."""
        from api.handlers import handle_model_names_and_ids
        result = await handle_model_names_and_ids(anki_wrapper, {})
        assert "Basic" in result

    @pytest.mark.asyncio
    async def test_handle_model_field_names(self, anki_wrapper):
        """Test modelFieldNames handler."""
        from api.handlers import handle_model_field_names
        result = await handle_model_field_names(anki_wrapper, {"modelName": "Basic"})
        assert "Front" in result
        assert "Back" in result

    @pytest.mark.asyncio
    async def test_handle_model_styling(self, anki_wrapper):
        """Test modelStyling handler."""
        from api.handlers import handle_model_styling
        result = await handle_model_styling(anki_wrapper, {"modelName": "Basic"})
        assert isinstance(result, dict)
        assert "css" in result


class TestNoteHandlers:
    """Test note-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_add_note(self, anki_wrapper):
        """Test addNote handler."""
        from api.handlers import handle_add_note
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
        from api.handlers import handle_add_notes
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
        from api.handlers import handle_update_note_fields
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
        from api.handlers import handle_can_add_notes
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
        from api.handlers import handle_find_notes
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "FindTest", "Back": "Test"}
        })
        result = await handle_find_notes(anki_wrapper, {"query": "FindTest"})
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_notes_info(self, anki_wrapper):
        """Test notesInfo handler."""
        from api.handlers import handle_notes_info
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
        from api.handlers import handle_delete_notes
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
        from api.handlers import handle_find_cards
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "CardTest", "Back": "Test"}
        })
        result = await handle_find_cards(anki_wrapper, {"query": "CardTest"})
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_handle_cards_to_notes(self, anki_wrapper):
        """Test cardsToNotes handler."""
        from api.handlers import handle_cards_to_notes
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
        from api.handlers import handle_cards_info
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
        from api.handlers import handle_suspend
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_suspend(anki_wrapper, {"cards": card_ids})
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_unsuspend(self, anki_wrapper):
        """Test unsuspend handler."""
        from api.handlers import handle_unsuspend
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
        from api.handlers import handle_are_suspended
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
    async def test_handle_are_due(self, anki_wrapper):
        """Test areDue handler."""
        from api.handlers import handle_are_due
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
        from api.handlers import handle_get_intervals
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = await handle_get_intervals(anki_wrapper, {"cards": card_ids})
        assert len(result) == 1


class TestMediaHandlers:
    """Test media-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_media_dir_path(self, anki_wrapper):
        """Test getMediaDirPath handler."""
        from api.handlers import handle_get_media_dir_path
        result = await handle_get_media_dir_path(anki_wrapper, {})
        assert result is not None
        assert len(result) > 0


class TestMultiHandler:
    """Test multi action handler."""

    @pytest.mark.asyncio
    async def test_handle_multi(self, anki_wrapper):
        """Test multi handler."""
        from api.handlers import handle_multi
        anki_wrapper.create_deck("MultiTest")
        result = await handle_multi(anki_wrapper, {
            "actions": [
                {"action": "deckNames", "params": {}},
                {"action": "modelNames", "params": {}}
            ]
        })
        assert len(result) == 2