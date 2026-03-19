"""Tests for API handlers."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from api.handlers import (
    handle_version,
    handle_deck_names,
    handle_deck_names_and_ids,
    handle_create_deck,
    handle_model_names,
    handle_model_field_names,
    handle_add_note,
    handle_find_notes,
    handle_notes_info,
    handle_delete_notes,
    handle_find_cards,
    handle_cards_info,
    handle_suspend,
    handle_unsuspend,
    handle_are_suspended,
    handle_are_due,
    handle_get_intervals,
    handle_get_tags,
    handle_add_tags,
    handle_remove_tags,
    handle_get_media_dir_path,
    handle_store_media_file,
    handle_retrieve_media_file,
    handle_delete_media_file,
    handle_multi,
    dispatch,
    API_VERSION,
)


class TestMiscHandlers:
    """Test miscellaneous handlers."""

    @pytest.mark.asyncio
    async def test_handle_version(self, mock_wrapper):
        """Test version handler."""
        result = await handle_version(mock_wrapper, {})
        assert result == API_VERSION

    @pytest.mark.asyncio
    async def test_handle_deck_names(self, mock_wrapper):
        """Test deckNames handler."""
        result = await handle_deck_names(mock_wrapper, {})
        assert result == ["Default", "Spanish"]

    @pytest.mark.asyncio
    async def test_handle_deck_names_and_ids(self, mock_wrapper):
        """Test deckNamesAndIds handler."""
        result = await handle_deck_names_and_ids(mock_wrapper, {})
        assert result == {"Default": 1, "Spanish": 2}

    @pytest.mark.asyncio
    async def test_handle_create_deck(self, mock_wrapper):
        """Test createDeck handler."""
        mock_wrapper.create_deck.return_value = 12345
        result = await handle_create_deck(mock_wrapper, {"deck": "NewDeck"})
        assert result == 12345
        mock_wrapper.create_deck.assert_called_once_with("NewDeck")

    @pytest.mark.asyncio
    async def test_handle_get_decks(self, mock_wrapper):
        """Test getDecks handler."""
        mock_wrapper.get_decks.return_value = {"Default": [1, 2, 3]}
        from api.handlers import handle_get_decks
        result = await handle_get_decks(mock_wrapper, {"cards": [1, 2, 3]})
        assert result == {"Default": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_handle_delete_decks(self, mock_wrapper):
        """Test deleteDecks handler."""
        from api.handlers import handle_delete_decks
        await handle_delete_decks(mock_wrapper, {"decks": ["Deck1"], "cardsToo": True})
        mock_wrapper.delete_decks.assert_called_once_with(["Deck1"], True)

    @pytest.mark.asyncio
    async def test_handle_change_deck(self, mock_wrapper):
        """Test changeDeck handler."""
        from api.handlers import handle_change_deck
        await handle_change_deck(mock_wrapper, {"cards": [1, 2], "deck": "NewDeck"})
        mock_wrapper.change_deck.assert_called_once_with([1, 2], "NewDeck")


class TestModelHandlers:
    """Test model-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_model_names(self, mock_wrapper):
        """Test modelNames handler."""
        mock_wrapper.model_names.return_value = ["Basic", "Cloze"]
        result = await handle_model_names(mock_wrapper, {})
        assert result == ["Basic", "Cloze"]

    @pytest.mark.asyncio
    async def test_handle_model_field_names(self, mock_wrapper):
        """Test modelFieldNames handler."""
        mock_wrapper.model_field_names.return_value = ["Front", "Back"]
        result = await handle_model_field_names(mock_wrapper, {"modelName": "Basic"})
        assert result == ["Front", "Back"]

    @pytest.mark.asyncio
    async def test_handle_model_fields_on_templates(self, mock_wrapper):
        """Test modelFieldsOnTemplates handler."""
        from api.handlers import handle_model_fields_on_templates
        mock_wrapper.model_fields_on_templates.return_value = {
            "Card 1": [["Front"], ["Back"]]
        }
        result = await handle_model_fields_on_templates(mock_wrapper, {"modelName": "Basic"})
        assert result == {"Card 1": [["Front"], ["Back"]]}

    @pytest.mark.asyncio
    async def test_handle_model_templates(self, mock_wrapper):
        """Test modelTemplates handler."""
        from api.handlers import handle_model_templates
        mock_wrapper.model_templates.return_value = {
            "Card 1": {"Front": "{{Front}}", "Back": "{{Back}}"}
        }
        result = await handle_model_templates(mock_wrapper, {"modelName": "Basic"})
        assert result == {"Card 1": {"Front": "{{Front}}", "Back": "{{Back}}"}}

    @pytest.mark.asyncio
    async def test_handle_model_styling(self, mock_wrapper):
        """Test modelStyling handler."""
        from api.handlers import handle_model_styling
        mock_wrapper.model_styling.return_value = {"css": ".card { font-size: 20px; }"}
        result = await handle_model_styling(mock_wrapper, {"modelName": "Basic"})
        assert result == {"css": ".card { font-size: 20px; }"}


class TestNoteHandlers:
    """Test note-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_add_note(self, mock_wrapper):
        """Test addNote handler."""
        note = {"deckName": "Default", "modelName": "Basic", "fields": {"Front": "Hello", "Back": "World"}}
        mock_wrapper.add_note.return_value = 12345
        result = await handle_add_note(mock_wrapper, {"note": note})
        assert result == 12345

    @pytest.mark.asyncio
    async def test_handle_add_note_invalid(self, mock_wrapper):
        """Test addNote handler with invalid note."""
        mock_wrapper.add_note.return_value = None
        result = await handle_add_note(mock_wrapper, {"note": {}})
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_add_notes(self, mock_wrapper):
        """Test addNotes handler."""
        notes = [
            {"deckName": "Default", "modelName": "Basic", "fields": {"Front": "Hello"}},
            {"deckName": "Default", "modelName": "Basic", "fields": {"Front": "World"}}
        ]
        mock_wrapper.add_notes.return_value = [123, 456]
        from api.handlers import handle_add_notes
        result = await handle_add_notes(mock_wrapper, {"notes": notes})
        assert result == [123, 456]

    @pytest.mark.asyncio
    async def test_handle_can_add_notes(self, mock_wrapper):
        """Test canAddNotes handler."""
        from api.handlers import handle_can_add_notes
        notes = [{"deckName": "Default", "modelName": "Basic", "fields": {"Front": "Hello"}}]
        mock_wrapper.can_add_notes.return_value = [True]
        result = await handle_can_add_notes(mock_wrapper, {"notes": notes})
        assert result == [True]

    @pytest.mark.asyncio
    async def test_handle_update_note_fields(self, mock_wrapper):
        """Test updateNoteFields handler."""
        from api.handlers import handle_update_note_fields
        note = {"id": 123, "fields": {"Front": "New Front"}}
        await handle_update_note_fields(mock_wrapper, {"note": note})
        mock_wrapper.update_note_fields.assert_called_once_with(note)

    @pytest.mark.asyncio
    async def test_handle_find_notes(self, mock_wrapper):
        """Test findNotes handler."""
        mock_wrapper.find_notes.return_value = [1, 2, 3, 4, 5]
        result = await handle_find_notes(mock_wrapper, {"query": "deck:Default"})
        assert result == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_handle_notes_info(self, mock_wrapper):
        """Test notesInfo handler."""
        notes_info = [{"noteId": 123, "modelName": "Basic", "tags": ["test"]}]
        mock_wrapper.notes_info.return_value = notes_info
        result = await handle_notes_info(mock_wrapper, {"notes": [123]})
        assert result == notes_info

    @pytest.mark.asyncio
    async def test_handle_delete_notes(self, mock_wrapper):
        """Test deleteNotes handler."""
        await handle_delete_notes(mock_wrapper, {"notes": [1, 2, 3]})
        mock_wrapper.delete_notes.assert_called_once_with([1, 2, 3])


class TestCardHandlers:
    """Test card-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_find_cards(self, mock_wrapper):
        """Test findCards handler."""
        mock_wrapper.find_cards.return_value = [1, 2, 3]
        result = await handle_find_cards(mock_wrapper, {"query": "deck:Default"})
        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_handle_cards_to_notes(self, mock_wrapper):
        """Test cardsToNotes handler."""
        from api.handlers import handle_cards_to_notes
        mock_wrapper.cards_to_notes.return_value = [1, 2]
        result = await handle_cards_to_notes(mock_wrapper, {"cards": [1, 2, 3]})
        assert result == [1, 2]

    @pytest.mark.asyncio
    async def test_handle_cards_info(self, mock_wrapper):
        """Test cardsInfo handler."""
        mock_wrapper.cards_info.return_value = [{"cardId": 1, "interval": 10}]
        result = await handle_cards_info(mock_wrapper, {"cards": [1]})
        assert result == [{"cardId": 1, "interval": 10}]

    @pytest.mark.asyncio
    async def test_handle_suspend(self, mock_wrapper):
        """Test suspend handler."""
        mock_wrapper.suspend.return_value = True
        result = await handle_suspend(mock_wrapper, {"cards": [1, 2, 3]})
        assert result is True
        mock_wrapper.suspend.assert_called_once_with([1, 2, 3])

    @pytest.mark.asyncio
    async def test_handle_unsuspend(self, mock_wrapper):
        """Test unsuspend handler."""
        mock_wrapper.unsuspend.return_value = True
        result = await handle_unsuspend(mock_wrapper, {"cards": [1, 2, 3]})
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_are_suspended(self, mock_wrapper):
        """Test areSuspended handler."""
        mock_wrapper.are_suspended.return_value = [True, False]
        result = await handle_are_suspended(mock_wrapper, {"cards": [1, 2]})
        assert result == [True, False]

    @pytest.mark.asyncio
    async def test_handle_are_due(self, mock_wrapper):
        """Test areDue handler."""
        mock_wrapper.are_due.return_value = [True, False]
        result = await handle_are_due(mock_wrapper, {"cards": [1, 2]})
        assert result == [True, False]

    @pytest.mark.asyncio
    async def test_handle_get_intervals(self, mock_wrapper):
        """Test getIntervals handler."""
        mock_wrapper.get_intervals.return_value = [10, 20]
        result = await handle_get_intervals(mock_wrapper, {"cards": [1, 2], "complete": False})
        assert result == [10, 20]


class TestTagHandlers:
    """Test tag-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_tags(self, mock_wrapper):
        """Test getTags handler."""
        mock_wrapper.get_tags.return_value = ["tag1", "tag2", "tag3"]
        result = await handle_get_tags(mock_wrapper, {})
        assert result == ["tag1", "tag2", "tag3"]

    @pytest.mark.asyncio
    async def test_handle_add_tags(self, mock_wrapper):
        """Test addTags handler."""
        await handle_add_tags(mock_wrapper, {"notes": [1, 2], "tags": "new_tag"})
        mock_wrapper.add_tags.assert_called_once_with([1, 2], "new_tag")

    @pytest.mark.asyncio
    async def test_handle_remove_tags(self, mock_wrapper):
        """Test removeTags handler."""
        await handle_remove_tags(mock_wrapper, {"notes": [1, 2], "tags": "old_tag"})
        mock_wrapper.remove_tags.assert_called_once_with([1, 2], "old_tag")


class TestMediaHandlers:
    """Test media-related handlers."""

    @pytest.mark.asyncio
    async def test_handle_get_media_dir_path(self, mock_wrapper):
        """Test getMediaDirPath handler."""
        mock_wrapper.get_media_dir_path.return_value = "/path/to/media"
        result = await handle_get_media_dir_path(mock_wrapper, {})
        assert result == "/path/to/media"

    @pytest.mark.asyncio
    async def test_handle_store_media_file(self, mock_wrapper):
        """Test storeMediaFile handler."""
        await handle_store_media_file(mock_wrapper, {"filename": "test.txt", "data": "SGVsbG8="})
        mock_wrapper.store_media_file.assert_called_once_with("test.txt", "SGVsbG8=")

    @pytest.mark.asyncio
    async def test_handle_retrieve_media_file(self, mock_wrapper):
        """Test retrieveMediaFile handler."""
        mock_wrapper.retrieve_media_file.return_value = "SGVsbG8="
        result = await handle_retrieve_media_file(mock_wrapper, {"filename": "test.txt"})
        assert result == "SGVsbG8="

    @pytest.mark.asyncio
    async def test_handle_delete_media_file(self, mock_wrapper):
        """Test deleteMediaFile handler."""
        await handle_delete_media_file(mock_wrapper, {"filename": "test.txt"})
        mock_wrapper.delete_media_file.assert_called_once_with("test.txt")


class TestMultiHandler:
    """Test multi-action handler."""

    @pytest.mark.asyncio
    async def test_handle_multi(self, mock_wrapper):
        """Test multi handler."""
        mock_wrapper.deck_names.return_value = ["Default"]
        mock_wrapper.model_names.return_value = ["Basic"]
        
        actions = [
            {"action": "deckNames", "params": {}},
            {"action": "modelNames", "params": {}}
        ]
        
        result = await handle_multi(mock_wrapper, {"actions": actions})
        assert result == [["Default"], ["Basic"]]

    @pytest.mark.asyncio
    async def test_handle_multi_with_invalid_action(self, mock_wrapper):
        """Test multi handler with invalid action."""
        actions = [{"action": "invalidAction", "params": {}}]
        result = await handle_multi(mock_wrapper, {"actions": actions})
        assert "error" in str(result[0])


class TestDispatch:
    """Test dispatch function."""

    @pytest.mark.asyncio
    async def test_dispatch_unknown_action(self, mock_wrapper):
        """Test dispatch with unknown action."""
        with pytest.raises(ValueError, match="Unsupported action"):
            await dispatch("unknownAction", {}, mock_wrapper)

    @pytest.mark.asyncio
    async def test_dispatch_valid_action(self, mock_wrapper):
        """Test dispatch with valid action."""
        mock_wrapper.deck_names.return_value = ["Default"]
        result = await dispatch("deckNames", {}, mock_wrapper)
        assert result == ["Default"]