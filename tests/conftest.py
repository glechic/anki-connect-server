import os
import tempfile
import pytest


os.environ["ANKICONNECT_COLLECTION_PATH"] = "/tmp/test_collection.anki21"


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


@pytest.fixture
def mock_wrapper():
    """Create a mock wrapper with mocked methods."""
    from unittest.mock import MagicMock
    
    wrapper = MagicMock()
    
    wrapper.deck_names.return_value = ["Default", "Spanish"]
    wrapper.deck_names_and_ids.return_value = {"Default": 1, "Spanish": 2}
    wrapper.create_deck.return_value = 12345
    wrapper.delete_decks.return_value = None
    wrapper.change_deck.return_value = None
    wrapper.get_decks.return_value = {"Default": [1, 2, 3]}
    
    wrapper.model_names.return_value = ["Basic", "Cloze"]
    wrapper.model_names_and_ids.return_value = {"Basic": 1, "Cloze": 2}
    wrapper.model_field_names.return_value = ["Front", "Back"]
    wrapper.model_fields_on_templates.return_value = {}
    wrapper.model_templates.return_value = {}
    wrapper.model_styling.return_value = {"css": ""}
    
    wrapper.add_note.return_value = 12345
    wrapper.add_notes.return_value = [12345]
    wrapper.can_add_notes.return_value = [True]
    wrapper.update_note_fields.return_value = None
    wrapper.find_notes.return_value = [1, 2, 3]
    wrapper.notes_info.return_value = [{"noteId": 1, "modelName": "Basic"}]
    wrapper.delete_notes.return_value = None
    
    wrapper.find_cards.return_value = [1, 2, 3]
    wrapper.cards_to_notes.return_value = [1, 2]
    wrapper.cards_info.return_value = [{"cardId": 1}]
    wrapper.suspend.return_value = True
    wrapper.unsuspend.return_value = True
    wrapper.are_suspended.return_value = [True]
    wrapper.are_due.return_value = [True]
    wrapper.get_intervals.return_value = [10]
    
    wrapper.get_tags.return_value = ["tag1", "tag2"]
    wrapper.add_tags.return_value = None
    wrapper.remove_tags.return_value = None
    
    wrapper.get_media_dir_path.return_value = "/path/to/media"
    wrapper.store_media_file.return_value = None
    wrapper.retrieve_media_file.return_value = "SGVsbG8="
    wrapper.delete_media_file.return_value = None
    
    wrapper.import_package.return_value = {}
    wrapper.export_package.return_value = None
    
    wrapper.get_deck_config.return_value = {}
    wrapper.save_deck_config.return_value = True
    wrapper.set_deck_config_id.return_value = True
    wrapper.clone_deck_config_id.return_value = 1
    wrapper.remove_deck_config_id.return_value = True
    
    wrapper.sync_to_ankiweb.return_value = "sync completed"
    wrapper.sync_media_only.return_value = "media sync completed"
    wrapper.sync_status.return_value = {"server": "ankiweb"}
    
    return wrapper