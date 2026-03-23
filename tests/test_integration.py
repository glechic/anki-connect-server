"""Integration tests using real AnkiWrapper."""

import os
import tempfile
import pytest


@pytest.fixture
def anki_wrapper():
    """Create an AnkiWrapper with temporary collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")

        from anki_wrapper import AnkiWrapper
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

    def test_list_models(self, anki_wrapper):
        """Test listing note models."""
        models = anki_wrapper.model_names()
        assert "Basic" in models

    def test_model_names_and_ids(self, anki_wrapper):
        """Test modelNamesAndIds."""
        models = anki_wrapper.model_names_and_ids()
        assert "Basic" in models

    def test_model_field_names(self, anki_wrapper):
        """Test getting field names for a model."""
        fields = anki_wrapper.model_field_names("Basic")
        assert "Front" in fields
        assert "Back" in fields

    def test_model_styling(self, anki_wrapper):
        """Test model_styling."""
        styling = anki_wrapper.model_styling("Basic")
        assert "css" in styling

    def test_add_note(self, anki_wrapper):
        """Test adding a note."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Answer"}
        })
        assert note_id is not None

    def test_add_notes(self, anki_wrapper):
        """Test adding multiple notes."""
        result = anki_wrapper.add_notes([
            {"deckName": "Default", "modelName": "Basic", "fields": {"Front": "1", "Back": "1"}},
            {"deckName": "Default", "modelName": "Basic", "fields": {"Front": "2", "Back": "2"}},
        ])
        assert len(result) == 2
        assert result[0] is not None
        assert result[1] is not None

    def test_update_note_fields(self, anki_wrapper):
        """Test updating note fields."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Original", "Back": "Test"}
        })
        anki_wrapper.update_note_fields({
            "id": note_id,
            "fields": {"Front": "Updated"}
        })

    def test_find_notes(self, anki_wrapper):
        """Test finding notes."""
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "FindMe", "Back": "Test"}
        })
        notes = anki_wrapper.find_notes("FindMe")
        assert len(notes) > 0

    def test_notes_info(self, anki_wrapper):
        """Test notesInfo."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        info = anki_wrapper.notes_info([note_id])
        assert len(info) == 1
        assert info[0]["noteId"] == note_id
        assert "fields" in info[0]
        assert "tags" in info[0]

    def test_delete_notes(self, anki_wrapper):
        """Test deleting notes."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "ToDelete", "Back": "Test"}
        })
        anki_wrapper.delete_notes([note_id])
        notes = anki_wrapper.find_notes("ToDelete")
        assert len(notes) == 0

    def test_find_cards(self, anki_wrapper):
        """Test finding cards."""
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "CardTest", "Back": "Test"}
        })
        cards = anki_wrapper.find_cards("CardTest")
        assert len(cards) > 0

    def test_cards_to_notes(self, anki_wrapper):
        """Test cardsToNotes."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        notes = anki_wrapper.cards_to_notes(card_ids)
        assert note_id in notes

    def test_cards_info(self, anki_wrapper):
        """Test cardsInfo."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        info = anki_wrapper.cards_info(card_ids)
        assert len(info) > 0
        assert "cardId" in info[0]
        assert "fields" in info[0]

    def test_suspend_unsuspend(self, anki_wrapper):
        """Test suspend and unsuspend."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")

        result = anki_wrapper.suspend(card_ids)
        assert result is True

        result = anki_wrapper.unsuspend(card_ids)
        assert result is True

    def test_are_suspended(self, anki_wrapper):
        """Test areSuspended."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = anki_wrapper.are_suspended(card_ids)
        assert len(result) == 1
        assert result[0] is False

    def test_are_due(self, anki_wrapper):
        """Test areDue."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = anki_wrapper.are_due(card_ids)
        assert len(result) == 1

    def test_get_intervals(self, anki_wrapper):
        """Test getIntervals."""
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        result = anki_wrapper.get_intervals(card_ids)
        assert len(result) == 1

        result_complete = anki_wrapper.get_intervals(card_ids, complete=True)
        assert len(result_complete) == 1
        assert isinstance(result_complete[0], dict)

    def test_get_tags(self, anki_wrapper):
        """Test getTags."""
        anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"},
            "tags": ["testtag"]
        })
        tags = anki_wrapper.get_tags()
        assert "testtag" in tags

    def test_get_media_dir_path(self, anki_wrapper):
        """Test getting media directory path."""
        media_path = anki_wrapper.get_media_dir_path()
        assert media_path is not None
        assert len(media_path) > 0

    def test_change_deck(self, anki_wrapper):
        """Test change_deck."""
        anki_wrapper.create_deck("Target")
        note_id = anki_wrapper.add_note({
            "deckName": "Default",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
        anki_wrapper.change_deck(card_ids, "Target")

    def test_delete_decks_with_cards(self, anki_wrapper):
        """Test deleteDecks with cardsToo=True."""
        anki_wrapper.create_deck("DeckWithCards")
        note_id = anki_wrapper.add_note({
            "deckName": "DeckWithCards",
            "modelName": "Basic",
            "fields": {"Front": "Test", "Back": "Test"}
        })
        card_ids = anki_wrapper.find_cards(f"deck:DeckWithCards")
        assert len(card_ids) > 0

        anki_wrapper.delete_decks(["DeckWithCards"], cards_too=True)
        decks = anki_wrapper.deck_names()
        assert "DeckWithCards" not in decks

    def test_get_api_version(self):
        """Test API version constant."""
        from api.handlers import API_VERSION
        assert API_VERSION == 6