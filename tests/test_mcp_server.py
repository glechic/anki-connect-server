"""Tests for MCP server functionality."""

import os
import tempfile
import pytest
from unittest.mock import patch


@pytest.fixture
def mcp_wrapper():
    """Create an AnkiWrapper for MCP testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")
        media_path = collection_path + "-media"
        os.makedirs(media_path, exist_ok=True)

        from anki_connect_server.anki_wrapper import AnkiWrapper
        wrapper = AnkiWrapper(collection_path)

        yield wrapper

        wrapper.close()


@pytest.fixture(autouse=True)
def patch_mcp_wrapper(mcp_wrapper):
    """Auto-patch the global _wrapper in mcp_server for each test."""
    from anki_connect_server import mcp_server
    original_wrapper = mcp_server._wrapper
    mcp_server._wrapper = mcp_wrapper
    yield mcp_wrapper
    mcp_server._wrapper = original_wrapper


class TestMCPWrapper:
    """Test MCP wrapper functions using AnkiWrapper directly."""

    def test_get_deck_names(self):
        """Test get_deck_names MCP tool."""
        from anki_connect_server.mcp_server import get_deck_names
        result = get_deck_names()
        assert "Default" in result

    def test_get_deck_names_and_ids(self):
        """Test get_deck_names_and_ids MCP tool."""
        from anki_connect_server.mcp_server import get_deck_names_and_ids
        result = get_deck_names_and_ids()
        assert "Default" in result

    def test_create_deck(self):
        """Test create_deck MCP tool."""
        from anki_connect_server.mcp_server import create_deck
        deck_id = create_deck("MCPTestDeck")
        assert deck_id > 0

    def test_delete_decks(self):
        """Test delete_decks MCP tool."""
        from anki_connect_server.mcp_server import create_deck, delete_decks
        create_deck("ToDeleteMCP")
        result = delete_decks(["ToDeleteMCP"])
        assert result is True

    def test_get_model_names(self):
        """Test get_model_names MCP tool."""
        from anki_connect_server.mcp_server import get_model_names
        result = get_model_names()
        assert "Basic" in result

    def test_get_model_field_names(self):
        """Test get_model_field_names MCP tool."""
        from anki_connect_server.mcp_server import get_model_field_names
        result = get_model_field_names("Basic")
        assert "Front" in result
        assert "Back" in result

    def test_add_note(self):
        """Test add_note MCP tool."""
        from anki_connect_server.mcp_server import add_note
        note_id = add_note("Default", "Basic", {"Front": "Test", "Back": "Answer"})
        assert note_id is not None

    def test_find_notes(self):
        """Test find_notes MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_notes
        add_note("Default", "Basic", {"Front": "FindMe", "Back": "Test"})
        result = find_notes("FindMe")
        assert len(result) > 0

    def test_get_notes_info(self):
        """Test get_notes_info MCP tool."""
        from anki_connect_server.mcp_server import add_note, get_notes_info
        note_id = add_note("Default", "Basic", {"Front": "Test", "Back": "Test"})
        result = get_notes_info([note_id])
        assert len(result) == 1
        assert result[0]["noteId"] == note_id

    def test_delete_notes(self):
        """Test delete_notes MCP tool."""
        from anki_connect_server.mcp_server import add_note, delete_notes
        note_id = add_note("Default", "Basic", {"Front": "ToDelete", "Back": "Test"})
        result = delete_notes([note_id])
        assert result is True

    def test_find_cards(self):
        """Test find_cards MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards
        add_note("Default", "Basic", {"Front": "CardTest", "Back": "Test"})
        result = find_cards("CardTest")
        assert len(result) > 0

    def test_get_cards_info(self):
        """Test get_cards_info MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, get_cards_info
        add_note("Default", "Basic", {"Front": "Test", "Back": "Test"})
        card_ids = find_cards("Test")
        result = get_cards_info(card_ids)
        assert len(result) > 0

    def test_suspend_cards(self):
        """Test suspend_cards MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, suspend_cards
        add_note("Default", "Basic", {"Front": "SuspendMe", "Back": "Test"})
        card_ids = find_cards("SuspendMe")
        result = suspend_cards(card_ids)
        assert result is True

    def test_unsuspend_cards(self):
        """Test unsuspend_cards MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, suspend_cards, unsuspend_cards
        add_note("Default", "Basic", {"Front": "UnsuspendMe", "Back": "Test"})
        card_ids = find_cards("UnsuspendMe")
        suspend_cards(card_ids)
        result = unsuspend_cards(card_ids)
        assert result is True

    def test_are_suspended(self):
        """Test are_suspended MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, suspend_cards, are_suspended
        add_note("Default", "Basic", {"Front": "SuspendedCheck", "Back": "Test"})
        card_ids = find_cards("SuspendedCheck")
        suspend_cards(card_ids)
        result = are_suspended(card_ids)
        assert result[0] is True

    def test_are_due(self):
        """Test are_due MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, are_due
        add_note("Default", "Basic", {"Front": "DueCheck", "Back": "Test"})
        card_ids = find_cards("DueCheck")
        result = are_due(card_ids)
        assert len(result) == 1

    def test_get_card_intervals(self):
        """Test get_card_intervals MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, get_card_intervals
        add_note("Default", "Basic", {"Front": "IntervalTest", "Back": "Test"})
        card_ids = find_cards("IntervalTest")
        result = get_card_intervals(card_ids)
        assert len(result) == 1

    def test_get_all_tags(self):
        """Test get_all_tags MCP tool."""
        from anki_connect_server.mcp_server import get_all_tags
        result = get_all_tags()
        assert isinstance(result, list)

    def test_get_media_dir_path(self):
        """Test get_media_dir_path MCP tool."""
        from anki_connect_server.mcp_server import get_media_dir_path
        result = get_media_dir_path()
        assert result is not None

    def test_cards_to_notes(self):
        """Test cards_to_notes MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, cards_to_notes
        note_id = add_note("Default", "Basic", {"Front": "CardsToNotes", "Back": "Test"})
        card_ids = find_cards("CardsToNotes")
        result = cards_to_notes(card_ids)
        assert note_id in result

    def test_change_deck(self):
        """Test change_deck MCP tool."""
        from anki_connect_server.mcp_server import add_note, find_cards, create_deck, change_deck
        create_deck("MCPNewDeck")
        note_id = add_note("Default", "Basic", {"Front": "MoveMe", "Back": "Test"})
        card_ids = find_cards("MoveMe")
        result = change_deck(card_ids, "MCPNewDeck")
        assert result is True

    def test_get_deck_config(self):
        """Test get_deck_config MCP tool."""
        from anki_connect_server.mcp_server import get_deck_config
        result = get_deck_config("Default")
        assert isinstance(result, dict)

    def test_get_model_templates(self):
        """Test get_model_templates MCP tool."""
        from anki_connect_server.mcp_server import get_model_templates
        result = get_model_templates("Basic")
        assert "Card 1" in result

    def test_get_model_styling(self):
        """Test get_model_styling MCP tool."""
        from anki_connect_server.mcp_server import get_model_styling
        result = get_model_styling("Basic")
        assert "css" in result

    def test_get_api_version(self):
        """Test get_api_version MCP tool."""
        from anki_connect_server.mcp_server import get_api_version
        result = get_api_version()
        assert result == 6
