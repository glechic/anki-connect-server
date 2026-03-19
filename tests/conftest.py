import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch


os.environ["ANKI_COLLECTION_PATH"] = "/tmp/test_collection.anki21"


@pytest.fixture
def anki_wrapper():
    """Create AnkiWrapper with mocked methods."""
    with patch("anki_wrapper.Collection") as mock_col_class:
        mock_instance = MagicMock()
        mock_col_class.return_value = mock_instance
        
        from anki_wrapper import AnkiWrapper
        wrapper = AnkiWrapper("/tmp/test.anki21")
        
        wrapper.deck_names = MagicMock(return_value=[])
        wrapper.deck_names_and_ids = MagicMock(return_value={})
        wrapper.create_deck = MagicMock(return_value=1)
        wrapper.delete_decks = MagicMock()
        wrapper.change_deck = MagicMock()
        wrapper.get_decks = MagicMock(return_value={})
        
        wrapper.model_names = MagicMock(return_value=[])
        wrapper.model_names_and_ids = MagicMock(return_value={})
        wrapper.model_field_names = MagicMock(return_value=[])
        wrapper.model_fields_on_templates = MagicMock(return_value={})
        wrapper.model_templates = MagicMock(return_value={})
        wrapper.model_styling = MagicMock(return_value={"css": ""})
        
        wrapper.add_note = MagicMock(return_value=12345)
        wrapper.add_notes = MagicMock(return_value=[12345])
        wrapper.can_add_notes = MagicMock(return_value=[True])
        wrapper.update_note_fields = MagicMock()
        wrapper.find_notes = MagicMock(return_value=[])
        wrapper.notes_info = MagicMock(return_value=[])
        wrapper.delete_notes = MagicMock()
        
        wrapper.find_cards = MagicMock(return_value=[])
        wrapper.cards_to_notes = MagicMock(return_value=[])
        wrapper.cards_info = MagicMock(return_value=[])
        wrapper.suspend = MagicMock(return_value=True)
        wrapper.unsuspend = MagicMock(return_value=True)
        wrapper.are_suspended = MagicMock(return_value=[])
        wrapper.are_due = MagicMock(return_value=[])
        wrapper.get_intervals = MagicMock(return_value=[])
        
        wrapper.get_tags = MagicMock(return_value=[])
        wrapper.add_tags = MagicMock()
        wrapper.remove_tags = MagicMock()
        
        wrapper.get_media_dir_path = MagicMock(return_value="/path/to/media")
        wrapper.store_media_file = MagicMock()
        wrapper.retrieve_media_file = MagicMock(return_value=None)
        wrapper.delete_media_file = MagicMock()
        
        wrapper.import_package = MagicMock(return_value={})
        wrapper.export_package = MagicMock()
        
        wrapper.get_deck_config = MagicMock(return_value={})
        wrapper.save_deck_config = MagicMock(return_value=True)
        wrapper.set_deck_config_id = MagicMock(return_value=True)
        wrapper.clone_deck_config_id = MagicMock(return_value=1)
        wrapper.remove_deck_config_id = MagicMock(return_value=True)
        
        wrapper.sync_to_ankiweb = MagicMock(return_value="sync completed")
        
        yield wrapper


@pytest.fixture
def temp_collection_path():
    """Create a temporary collection file path."""
    with tempfile.NamedTemporaryFile(suffix=".anki21", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_note():
    """Sample note data for testing."""
    return {
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {
            "Front": "Hello",
            "Back": "World"
        },
        "tags": ["test", "api"]
    }


@pytest.fixture
def sample_deck_config():
    """Sample deck configuration for testing."""
    return {
        "id": 1,
        "name": "Default",
        "new": {
            "perDay": 20,
            "delays": [1, 10]
        },
        "rev": {
            "perDay": 100
        }
    }