"""Tests for sync server functionality."""

import os
import tempfile
import multiprocessing
import time
import pytest


SYNC_USER = "testuser"
SYNC_PASS = "testpass"
SYNC_PORT = 18770
SYNC_HOST = "127.0.0.1"


def run_sync_server(host: str, port: int, user: str, password: str):  # pragma: no cover
    """Entry point for the sync server process."""
    os.environ["SYNC_HOST"] = host
    os.environ["SYNC_PORT"] = str(port)
    os.environ["SYNC_USER1"] = f"{user}:{password}"
    from anki._backend import RustBackend
    RustBackend.syncserver()


@pytest.fixture
def sync_server():
    """Provide a running sync server."""
    process = multiprocessing.Process(
        target=run_sync_server,
        args=(SYNC_HOST, SYNC_PORT, SYNC_USER, SYNC_PASS),
    )
    process.start()
    time.sleep(2)

    yield f"http://{SYNC_HOST}:{SYNC_PORT}"

    process.terminate()
    process.join(timeout=5)
    if process.is_alive():  # pragma: no cover
        process.kill()
        process.join(timeout=5)


@pytest.fixture
def sync_anki_wrapper(sync_server):
    """Create an AnkiWrapper configured to use the sync server."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")

        from anki_wrapper import AnkiWrapper
        wrapper = AnkiWrapper(collection_path)

        yield wrapper, sync_server

        wrapper.close()


class TestSyncServer:
    """Test sync to local sync server."""

    @pytest.mark.asyncio
    async def test_sync_status_to_local_server(self, sync_anki_wrapper):
        """Test that we can get sync status from a local sync server.

        This test verifies that:
        1. The sync server starts correctly
        2. The AnkiWrapper can connect to it
        3. sync_status returns valid response
        """
        from api.handlers import handle_sync_status

        wrapper, endpoint = sync_anki_wrapper
        result = await handle_sync_status(wrapper, {
            "endpoint": endpoint,
            "username": SYNC_USER,
            "password": SYNC_PASS,
        })
        assert isinstance(result, dict)
        assert "server" in result or "status" in result

    @pytest.mark.asyncio
    async def test_sync_to_local_server(self, sync_anki_wrapper):
        """Test that we can sync to a local sync server.

        This test verifies that:
        1. The sync server accepts connections
        2. AnkiWrapper.sync_to_ankiweb works with custom credentials
        """
        from api.handlers import handle_sync

        wrapper, endpoint = sync_anki_wrapper
        result = await handle_sync(wrapper, {
            "endpoint": endpoint,
            "username": SYNC_USER,
            "password": SYNC_PASS,
        })
        assert isinstance(result, str)
        assert "sync completed" in result.lower()

    @pytest.mark.asyncio
    async def test_get_sync_auth(self, sync_anki_wrapper):
        """Test get_sync_auth with sync server credentials."""
        wrapper, endpoint = sync_anki_wrapper
        result = wrapper.get_sync_auth()
        assert result is not None
        assert hasattr(result, "hkey")

    @pytest.mark.asyncio
    async def test_sync_media_only(self, sync_anki_wrapper):
        """Test sync_media_only with sync server credentials."""
        from api.handlers import handle_sync_media

        wrapper, endpoint = sync_anki_wrapper
        result = await handle_sync_media(wrapper, {
            "endpoint": endpoint,
            "username": SYNC_USER,
            "password": SYNC_PASS,
        })
        assert isinstance(result, str)
        assert "media" in result.lower()
