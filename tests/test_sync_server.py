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
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    from anki._backend import RustBackend
    RustBackend.syncserver()


@pytest.fixture(autouse=True, scope='module')
def sync_server():
    """Provide a running sync server."""
    process = multiprocessing.Process(
        target=run_sync_server,
        args=(SYNC_HOST, SYNC_PORT, SYNC_USER, SYNC_PASS),
        daemon=True
    )
    process.start()
    time.sleep(2)

    yield f"http://{SYNC_HOST}:{SYNC_PORT}"

    process.terminate()
    process.join(timeout=5)
    if process.is_alive():
        process.kill()
        process.join(timeout=2)
    try:
        process.close()
    except ValueError:
        pass  # Already terminated


@pytest.fixture
def sync_anki_wrapper(sync_server):
    """Create an AnkiWrapper configured to use the sync server."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")

        from anki_connect_server.anki_wrapper import AnkiWrapper
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
        from anki_connect_server.handlers import handle_sync_status

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
        from anki_connect_server.handlers import handle_sync

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
        from anki_connect_server.handlers import handle_sync_media

        wrapper, endpoint = sync_anki_wrapper
        result = await handle_sync_media(wrapper, {
            "endpoint": endpoint,
            "username": SYNC_USER,
            "password": SYNC_PASS,
        })
        assert isinstance(result, str)
        assert "media" in result.lower()

    @pytest.mark.asyncio
    async def test_sync_media_only_with_missing_credentials(self, anki_wrapper):
        """Test sync_media_only raises error when credentials are missing."""
        from anki_connect_server.handlers import handle_sync_media
        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = None
        config.ANKIWEB_PASS = None

        try:
            with pytest.raises(ValueError, match="required for media sync"):
                await handle_sync_media(anki_wrapper, {})
        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    @pytest.mark.asyncio
    async def test_sync_media_only_partial_params(self, sync_anki_wrapper):
        """Test sync_media_only works with only username in params (password from config)."""
        from anki_connect_server.handlers import handle_sync_media
        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = SYNC_USER
        config.ANKIWEB_PASS = SYNC_PASS

        wrapper, endpoint = sync_anki_wrapper
        try:
            result = await handle_sync_media(wrapper, {"endpoint": endpoint})
            assert isinstance(result, str)
            assert "media" in result.lower()
        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass


class TestMediaFileOperations:
    """Test media file operations with local sync server."""

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_media_file(self, sync_anki_wrapper):
        """Test retrieving a file that doesn't exist returns None."""
        from anki_connect_server.handlers import handle_retrieve_media_file

        wrapper, endpoint = sync_anki_wrapper
        result = await handle_retrieve_media_file(wrapper, {"filename": "nonexistent.txt"})
        assert result is None

    @pytest.mark.asyncio
    async def test_media_dir_path(self, sync_anki_wrapper):
        """Test getting media directory path."""
        from anki_connect_server.handlers import handle_get_media_dir_path

        wrapper, endpoint = sync_anki_wrapper
        result = await handle_get_media_dir_path(wrapper, {})
        assert result is not None
        assert len(result) > 0
