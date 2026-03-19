"""Integration tests for the FastAPI server."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
def mock_wrapper():
    """Create a mock AnkiWrapper."""
    wrapper = MagicMock()
    wrapper.deck_names = MagicMock(return_value=["Default", "Spanish"])
    wrapper.deck_names_and_ids = MagicMock(return_value={"Default": 1, "Spanish": 2})
    wrapper.create_deck = MagicMock(return_value=12345)
    wrapper.model_names = MagicMock(return_value=["Basic", "Cloze"])
    wrapper.model_field_names = MagicMock(return_value=["Front", "Back"])
    wrapper.add_note = MagicMock(return_value=12345)
    wrapper.find_notes = MagicMock(return_value=[1, 2, 3])
    wrapper.notes_info = MagicMock(return_value=[{"noteId": 1, "modelName": "Basic"}])
    wrapper.delete_notes = MagicMock()
    wrapper.find_cards = MagicMock(return_value=[1, 2, 3])
    wrapper.cards_info = MagicMock(return_value=[{"cardId": 1, "interval": 10}])
    wrapper.suspend = MagicMock(return_value=True)
    wrapper.unsuspend = MagicMock(return_value=True)
    wrapper.are_suspended = MagicMock(return_value=[True])
    wrapper.are_due = MagicMock(return_value=[True])
    wrapper.get_intervals = MagicMock(return_value=[10])
    wrapper.get_tags = MagicMock(return_value=["tag1", "tag2"])
    wrapper.add_tags = MagicMock()
    wrapper.remove_tags = MagicMock()
    wrapper.get_media_dir_path = MagicMock(return_value="/path/to/media")
    wrapper.store_media_file = MagicMock()
    wrapper.retrieve_media_file = MagicMock(return_value="SGVsbG8=")
    wrapper.delete_media_file = MagicMock()
    wrapper.sync_to_ankiweb = MagicMock(return_value="sync completed")
    return wrapper


@pytest.fixture
def app_with_mock(mock_wrapper):
    """Patch the app to use mock wrapper."""
    with patch("main.wrapper", mock_wrapper):
        yield mock_wrapper


@pytest.mark.asyncio
async def test_root_endpoint(app_with_mock):
    """Test root endpoint returns health message."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "version", "version": 6})
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint(app_with_mock):
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_version_action(app_with_mock):
    """Test version action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "version", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 6
        assert data["error"] is None


@pytest.mark.asyncio
async def test_deck_names_action(app_with_mock):
    """Test deckNames action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "deckNames", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == ["Default", "Spanish"]
        assert data["error"] is None


@pytest.mark.asyncio
async def test_deck_names_and_ids_action(app_with_mock):
    """Test deckNamesAndIds action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "deckNamesAndIds", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == {"Default": 1, "Spanish": 2}


@pytest.mark.asyncio
async def test_create_deck_action(app_with_mock):
    """Test createDeck action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "createDeck",
            "version": 6,
            "params": {"deck": "NewDeck"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 12345


@pytest.mark.asyncio
async def test_model_names_action(app_with_mock):
    """Test modelNames action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "modelNames", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == ["Basic", "Cloze"]


@pytest.mark.asyncio
async def test_model_field_names_action(app_with_mock):
    """Test modelFieldNames action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "modelFieldNames",
            "version": 6,
            "params": {"modelName": "Basic"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == ["Front", "Back"]


@pytest.mark.asyncio
async def test_add_note_action(app_with_mock):
    """Test addNote action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": "Default",
                    "modelName": "Basic",
                    "fields": {"Front": "Hello", "Back": "World"}
                }
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 12345


@pytest.mark.asyncio
async def test_find_notes_action(app_with_mock):
    """Test findNotes action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "findNotes",
            "version": 6,
            "params": {"query": "deck:Default"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_notes_info_action(app_with_mock):
    """Test notesInfo action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "notesInfo",
            "version": 6,
            "params": {"notes": [1]}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == [{"noteId": 1, "modelName": "Basic"}]


@pytest.mark.asyncio
async def test_delete_notes_action(app_with_mock):
    """Test deleteNotes action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "deleteNotes",
            "version": 6,
            "params": {"notes": [1, 2, 3]}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None


@pytest.mark.asyncio
async def test_find_cards_action(app_with_mock):
    """Test findCards action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "findCards",
            "version": 6,
            "params": {"query": "deck:Default"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_cards_info_action(app_with_mock):
    """Test cardsInfo action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "cardsInfo",
            "version": 6,
            "params": {"cards": [1]}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == [{"cardId": 1, "interval": 10}]


@pytest.mark.asyncio
async def test_suspend_action(app_with_mock):
    """Test suspend action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "suspend",
            "version": 6,
            "params": {"cards": [1, 2, 3]}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] is True


@pytest.mark.asyncio
async def test_unsuspend_action(app_with_mock):
    """Test unsuspend action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "unsuspend",
            "version": 6,
            "params": {"cards": [1, 2, 3]}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] is True


@pytest.mark.asyncio
async def test_get_tags_action(app_with_mock):
    """Test getTags action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "getTags", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == ["tag1", "tag2"]


@pytest.mark.asyncio
async def test_get_media_dir_path_action(app_with_mock):
    """Test getMediaDirPath action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "getMediaDirPath", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "/path/to/media"


@pytest.mark.asyncio
async def test_sync_action(app_with_mock):
    """Test sync action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "sync", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert "sync" in data["result"]


@pytest.mark.asyncio
async def test_multi_action(app_with_mock):
    """Test multi action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "multi",
            "version": 6,
            "params": {
                "actions": [
                    {"action": "deckNames", "params": {}},
                    {"action": "modelNames", "params": {}}
                ]
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == [["Default", "Spanish"], ["Basic", "Cloze"]]


@pytest.mark.asyncio
async def test_unknown_action(app_with_mock):
    """Test unknown action returns error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "unknownAction", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert "Unsupported action" in data["error"]


@pytest.mark.asyncio
async def test_invalid_json(app_with_mock):
    """Test invalid JSON request."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", content="invalid json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422  # Validation error