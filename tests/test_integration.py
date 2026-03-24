"""Integration tests using real AnkiWrapper."""

import os
import tempfile
import pytest


@pytest.fixture
def anki_wrapper():
    """Create an AnkiWrapper with temporary collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")

        from anki_connect_server.anki_wrapper import AnkiWrapper
        wrapper = AnkiWrapper(collection_path)

        yield wrapper

        wrapper.close()


class TestAnkiWrapperIntegration:
    """Integration tests for AnkiWrapper."""

    def test_create_and_list_decks(self, anki_wrapper):
        """Test creating and listing decks."""
        deck_id = anki_wrapper.create_deck("TestDeck")
        assert deck_id > 0

        decks = anki_wrapper.deck_names()
        assert "TestDeck" in decks

    def test_create_multiple_decks(self, anki_wrapper):
        """Test creating multiple decks."""
        anki_wrapper.create_deck("Deck1")
        anki_wrapper.create_deck("Deck2")

        decks = anki_wrapper.deck_names()
        assert "Deck1" in decks
        assert "Deck2" in decks

    def test_deck_names_and_ids(self, anki_wrapper):
        """Test getting deck names and IDs."""
        deck_id = anki_wrapper.create_deck("IDTestDeck")

        decks = anki_wrapper.deck_names_and_ids()
        assert "IDTestDeck" in decks
        assert decks["IDTestDeck"] == deck_id

    def test_delete_deck(self, anki_wrapper):
        """Test deleting a deck."""
        anki_wrapper.create_deck("ToDelete")
        anki_wrapper.delete_decks(["ToDelete"])

        decks = anki_wrapper.deck_names()
        assert "ToDelete" not in decks

    def test_get_decks(self, anki_wrapper):
        """Test get_decks returns correct mapping."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = anki_wrapper.get_decks(card_ids)
        assert "Default" in result
        assert card_ids[0] in result["Default"]

    def test_get_decks_empty(self, anki_wrapper):
        """Test get_decks with empty list."""
        result = anki_wrapper.get_decks([])
        assert result == {}

    def test_get_deck_config(self, anki_wrapper):
        """Test get_deck_config."""
        result = anki_wrapper.get_deck_config("Default")
        assert isinstance(result, dict)
        assert "name" in result

    def test_create_model(self, anki_wrapper):
        """Test create_model."""
        anki_wrapper.create_model(
            "TestModel",
            ["Field1", "Field2"],
            [{"Name": "Card 1", "Front": "{{Field1}}", "Back": "{{Field2}}"}],
            css=".card { }"
        )
        models = anki_wrapper.model_names()
        assert "TestModel" in models

    def test_model_templates(self, anki_wrapper):
        """Test model_templates."""
        result = anki_wrapper.model_templates("Basic")
        assert isinstance(result, dict)
        assert "Card 1" in result

    def test_update_model_templates(self, anki_wrapper):
        """Test update_model_templates."""
        result = anki_wrapper.update_model_templates({
            "name": "Basic",
            "templates": {
                "Card 1": {
                    "Front": "{{Front}}",
                    "Back": "{{Back}}"
                }
            }
        })
        assert result is None

    def test_update_model_styling(self, anki_wrapper):
        """Test update_model_styling."""
        result = anki_wrapper.update_model_styling({
            "name": "Basic",
            "css": ".card { background: #fff; }"
        })
        assert result is None

    def test_get_api_version(self):
        """Test API version constant."""
        from api.handlers import API_VERSION
        assert API_VERSION == 6