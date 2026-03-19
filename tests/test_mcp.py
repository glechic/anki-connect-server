"""Tests for MCP server."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestMCPServer:
    """Test MCP server tools."""

    @pytest.fixture
    def mock_wrapper(self):
        """Create mock AnkiWrapper."""
        wrapper = MagicMock()
        wrapper.deck_names.return_value = ["Default", "Spanish"]
        wrapper.deck_names_and_ids.return_value = {"Default": 1, "Spanish": 2}
        wrapper.create_deck.return_value = 12345
        wrapper.model_names.return_value = ["Basic", "Cloze"]
        wrapper.model_field_names.return_value = ["Front", "Back"]
        wrapper.add_note.return_value = 12345
        wrapper.find_notes.return_value = [1, 2, 3]
        wrapper.notes_info.return_value = [{"noteId": 1}]
        wrapper.delete_notes = MagicMock()
        wrapper.find_cards.return_value = [1, 2, 3]
        wrapper.cards_info.return_value = [{"cardId": 1}]
        wrapper.suspend.return_value = True
        wrapper.unsuspend.return_value = True
        wrapper.are_suspended.return_value = [True]
        wrapper.are_due.return_value = [True]
        wrapper.get_intervals.return_value = [10]
        wrapper.get_tags.return_value = ["tag1", "tag2"]
        wrapper.add_tags = MagicMock()
        wrapper.remove_tags = MagicMock()
        wrapper.get_media_dir_path.return_value = "/path/to/media"
        wrapper.store_media_file = MagicMock()
        wrapper.retrieve_media_file.return_value = "SGVsbG8="
        wrapper.delete_media_file = MagicMock()
        wrapper.import_package.return_value = {}
        wrapper.export_package = MagicMock()
        wrapper.sync_to_ankiweb.return_value = "sync completed"
        wrapper.sync_media_only.return_value = "media sync completed"
        wrapper.sync_status.return_value = {"server": "ankiweb", "status": "ok"}
        wrapper.change_deck = MagicMock()
        wrapper.cards_to_notes.return_value = [1, 2]
        wrapper.get_deck_config.return_value = {}
        wrapper.model_templates.return_value = {}
        wrapper.model_styling.return_value = {"css": ""}
        return wrapper

    def test_get_deck_names(self, mock_wrapper):
        """Test get_deck_names tool."""
        from mcp_server import get_deck_names
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_deck_names()
            assert result == ["Default", "Spanish"]

    def test_get_deck_names_and_ids(self, mock_wrapper):
        """Test get_deck_names_and_ids tool."""
        from mcp_server import get_deck_names_and_ids
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_deck_names_and_ids()
            assert result == {"Default": 1, "Spanish": 2}

    def test_create_deck(self, mock_wrapper):
        """Test create_deck tool."""
        from mcp_server import create_deck
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = create_deck("NewDeck")
            assert result == 12345
            mock_wrapper.create_deck.assert_called_once_with("NewDeck")

    def test_delete_decks(self, mock_wrapper):
        """Test delete_decks tool."""
        from mcp_server import delete_decks
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = delete_decks(["Deck1"], cards_too=True)
            assert result is True
            mock_wrapper.delete_decks.assert_called_once_with(["Deck1"], True)

    def test_get_model_names(self, mock_wrapper):
        """Test get_model_names tool."""
        from mcp_server import get_model_names
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_model_names()
            assert result == ["Basic", "Cloze"]

    def test_get_model_field_names(self, mock_wrapper):
        """Test get_model_field_names tool."""
        from mcp_server import get_model_field_names
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_model_field_names("Basic")
            assert result == ["Front", "Back"]

    def test_add_note(self, mock_wrapper):
        """Test add_note tool."""
        from mcp_server import add_note
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = add_note(
                deck_name="Default",
                model_name="Basic",
                fields={"Front": "Hello", "Back": "World"},
                tags=["test"]
            )
            assert result == 12345

    def test_find_notes(self, mock_wrapper):
        """Test find_notes tool."""
        from mcp_server import find_notes
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = find_notes("deck:Default")
            assert result == [1, 2, 3]
            mock_wrapper.find_notes.assert_called_once_with("deck:Default")

    def test_get_notes_info(self, mock_wrapper):
        """Test get_notes_info tool."""
        from mcp_server import get_notes_info
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_notes_info([1])
            assert result == [{"noteId": 1}]

    def test_delete_notes(self, mock_wrapper):
        """Test delete_notes tool."""
        from mcp_server import delete_notes
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = delete_notes([1, 2, 3])
            assert result is True
            mock_wrapper.delete_notes.assert_called_once_with([1, 2, 3])

    def test_find_cards(self, mock_wrapper):
        """Test find_cards tool."""
        from mcp_server import find_cards
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = find_cards("deck:Default")
            assert result == [1, 2, 3]

    def test_get_cards_info(self, mock_wrapper):
        """Test get_cards_info tool."""
        from mcp_server import get_cards_info
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_cards_info([1])
            assert result == [{"cardId": 1}]

    def test_suspend_cards(self, mock_wrapper):
        """Test suspend_cards tool."""
        from mcp_server import suspend_cards
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = suspend_cards([1, 2, 3])
            assert result is True

    def test_unsuspend_cards(self, mock_wrapper):
        """Test unsuspend_cards tool."""
        from mcp_server import unsuspend_cards
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = unsuspend_cards([1, 2, 3])
            assert result is True

    def test_are_suspended(self, mock_wrapper):
        """Test are_suspended tool."""
        from mcp_server import are_suspended
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = are_suspended([1])
            assert result == [True]

    def test_are_due(self, mock_wrapper):
        """Test are_due tool."""
        from mcp_server import are_due
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = are_due([1])
            assert result == [True]

    def test_get_card_intervals(self, mock_wrapper):
        """Test get_card_intervals tool."""
        from mcp_server import get_card_intervals
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_card_intervals([1, 2])
            assert result == [10]

    def test_get_all_tags(self, mock_wrapper):
        """Test get_all_tags tool."""
        from mcp_server import get_all_tags
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_all_tags()
            assert result == ["tag1", "tag2"]

    def test_add_tags(self, mock_wrapper):
        """Test add_tags tool."""
        from mcp_server import add_tags
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = add_tags([1, 2], "new_tag")
            assert result is True

    def test_remove_tags(self, mock_wrapper):
        """Test remove_tags tool."""
        from mcp_server import remove_tags
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = remove_tags([1, 2], "old_tag")
            assert result is True

    def test_get_media_dir_path(self, mock_wrapper):
        """Test get_media_dir_path tool."""
        from mcp_server import get_media_dir_path
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_media_dir_path()
            assert result == "/path/to/media"

    def test_store_media_file(self, mock_wrapper):
        """Test store_media_file tool."""
        from mcp_server import store_media_file
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = store_media_file("test.txt", "SGVsbG8=")
            assert result is True

    def test_retrieve_media_file(self, mock_wrapper):
        """Test retrieve_media_file tool."""
        from mcp_server import retrieve_media_file
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = retrieve_media_file("test.txt")
            assert result == "SGVsbG8="

    def test_delete_media_file(self, mock_wrapper):
        """Test delete_media_file tool."""
        from mcp_server import delete_media_file
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = delete_media_file("test.txt")
            assert result is True

    def test_import_package(self, mock_wrapper):
        """Test import_package tool."""
        from mcp_server import import_package
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = import_package("/path/to/file.apkg")
            assert result == {}

    def test_export_package(self, mock_wrapper):
        """Test export_package tool."""
        from mcp_server import export_package
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = export_package("Default", "/output.apkg")
            assert result is True

    def test_sync(self, mock_wrapper):
        """Test sync tool."""
        from mcp_server import sync
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = sync()
            assert result == "sync completed"

    def test_sync_media(self, mock_wrapper):
        """Test sync_media tool."""
        from mcp_server import sync_media
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = sync_media()
            assert result == "media sync completed"

    def test_get_sync_status(self, mock_wrapper):
        """Test get_sync_status tool."""
        from mcp_server import get_sync_status
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_sync_status()
            assert result == {"server": "ankiweb", "status": "ok"}

    def test_get_api_version(self):
        """Test get_api_version tool."""
        from mcp_server import get_api_version
        assert get_api_version() == 6

    def test_change_deck(self, mock_wrapper):
        """Test change_deck tool."""
        from mcp_server import change_deck
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = change_deck([1, 2], "NewDeck")
            assert result is True

    def test_cards_to_notes(self, mock_wrapper):
        """Test cards_to_notes tool."""
        from mcp_server import cards_to_notes
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = cards_to_notes([1, 2, 3])
            assert result == [1, 2]

    def test_get_deck_config(self, mock_wrapper):
        """Test get_deck_config tool."""
        from mcp_server import get_deck_config
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_deck_config("Default")
            assert result == {}

    def test_get_model_templates(self, mock_wrapper):
        """Test get_model_templates tool."""
        from mcp_server import get_model_templates
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_model_templates("Basic")
            assert result == {}

    def test_get_model_styling(self, mock_wrapper):
        """Test get_model_styling tool."""
        from mcp_server import get_model_styling
        with patch("mcp_server.get_wrapper", return_value=mock_wrapper):
            result = get_model_styling("Basic")
            assert result == {"css": ""}