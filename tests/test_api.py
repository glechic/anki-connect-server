"""Integration tests for the FastAPI server."""

import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
def app_with_wrapper(anki_wrapper):
    """Patch the app to use the real anki_wrapper."""
    with patch("main.wrapper", anki_wrapper):
        yield anki_wrapper


@pytest.mark.asyncio
async def test_root_endpoint(app_with_wrapper):
    """Test root endpoint returns health message."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "version", "version": 6})
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint(app_with_wrapper):
    """Test health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_version_action(app_with_wrapper):
    """Test version action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "version", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 6
        assert data["error"] is None


@pytest.mark.asyncio
async def test_deck_names_action(app_with_wrapper):
    """Test deckNames action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "deckNames", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert "Default" in data["result"]
        assert data["error"] is None


@pytest.mark.asyncio
async def test_deck_names_and_ids_action(app_with_wrapper):
    """Test deckNamesAndIds action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "deckNamesAndIds", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert "Default" in data["result"]


@pytest.mark.asyncio
async def test_create_deck_action(app_with_wrapper):
    """Test createDeck action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "createDeck",
            "version": 6,
            "params": {"deck": "NewDeck"}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] > 0


@pytest.mark.asyncio
async def test_model_names_action(app_with_wrapper):
    """Test modelNames action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "modelNames", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert "Basic" in data["result"]


@pytest.mark.asyncio
async def test_model_field_names_action(app_with_wrapper):
    """Test modelFieldNames action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "modelFieldNames",
            "version": 6,
            "params": {"modelName": "Basic"}
        })
        assert response.status_code == 200
        data = response.json()
        assert "Front" in data["result"]
        assert "Back" in data["result"]


@pytest.mark.asyncio
async def test_add_note_action(app_with_wrapper):
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
        assert data["result"] is not None


@pytest.mark.asyncio
async def test_find_notes_action(app_with_wrapper):
    """Test findNotes action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "findNotes",
            "version": 6,
            "params": {"query": "deck:Default"}
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["result"], list)


@pytest.mark.asyncio
async def test_notes_info_action(app_with_wrapper):
    """Test notesInfo action."""
    anki_wrapper = app_with_wrapper
    note_id = anki_wrapper.add_note({
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Test", "Back": "Test"}
    })
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "notesInfo",
            "version": 6,
            "params": {"notes": [note_id]}
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]) == 1
        assert data["result"][0]["noteId"] == note_id


@pytest.mark.asyncio
async def test_delete_notes_action(app_with_wrapper):
    """Test deleteNotes action."""
    anki_wrapper = app_with_wrapper
    note_id = anki_wrapper.add_note({
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Test", "Back": "Test"}
    })
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "deleteNotes",
            "version": 6,
            "params": {"notes": [note_id]}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None


@pytest.mark.asyncio
async def test_find_cards_action(app_with_wrapper):
    """Test findCards action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "findCards",
            "version": 6,
            "params": {"query": "deck:Default"}
        })
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["result"], list)


@pytest.mark.asyncio
async def test_cards_info_action(app_with_wrapper):
    """Test cardsInfo action."""
    anki_wrapper = app_with_wrapper
    note_id = anki_wrapper.add_note({
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Test", "Back": "Test"}
    })
    card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "cardsInfo",
            "version": 6,
            "params": {"cards": card_ids}
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data["result"]) > 0


@pytest.mark.asyncio
async def test_suspend_action(app_with_wrapper):
    """Test suspend action."""
    anki_wrapper = app_with_wrapper
    note_id = anki_wrapper.add_note({
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Test", "Back": "Test"}
    })
    card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "suspend",
            "version": 6,
            "params": {"cards": card_ids}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] is True


@pytest.mark.asyncio
async def test_unsuspend_action(app_with_wrapper):
    """Test unsuspend action."""
    anki_wrapper = app_with_wrapper
    note_id = anki_wrapper.add_note({
        "deckName": "Default",
        "modelName": "Basic",
        "fields": {"Front": "Test", "Back": "Test"}
    })
    card_ids = anki_wrapper.find_cards(f"nid:{note_id}")
    anki_wrapper.suspend(card_ids)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={
            "action": "unsuspend",
            "version": 6,
            "params": {"cards": card_ids}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["result"] is True


@pytest.mark.asyncio
async def test_get_tags_action(app_with_wrapper):
    """Test getTags action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "getTags", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["result"], list)


@pytest.mark.asyncio
async def test_get_media_dir_path_action(app_with_wrapper):
    """Test getMediaDirPath action."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "getMediaDirPath", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["result"] is not None


@pytest.mark.asyncio
async def test_multi_action(app_with_wrapper):
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
        assert len(data["result"]) == 2


@pytest.mark.asyncio
async def test_unknown_action(app_with_wrapper):
    """Test unknown action returns error."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", json={"action": "unknownAction", "version": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is not None
        assert "Unsupported action" in data["error"]


@pytest.mark.asyncio
async def test_invalid_json(app_with_wrapper):
    """Test invalid JSON request."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/", content="invalid json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422
