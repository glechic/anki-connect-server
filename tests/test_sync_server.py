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


def run_sync_server(host: str, port: int, user: str, password: str):
    """Entry point for the sync server process."""
    os.environ["SYNC_HOST"] = host
    os.environ["SYNC_PORT"] = str(port)
    os.environ["SYNC_USER1"] = f"{user}:{password}"
    from anki._backend import RustBackend
    RustBackend.syncserver()


class SyncServer:
    """Context manager for running a sync server in a multiprocessing.Process."""

    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.process = None

    def __enter__(self):
        self.process = multiprocessing.Process(
            target=run_sync_server,
            args=(self.host, self.port, self.user, self.password),
        )
        self.process.start()
        time.sleep(2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=5)
        return False

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@pytest.fixture
def sync_server():
    """Provide a running sync server."""
    server = SyncServer(SYNC_HOST, SYNC_PORT, SYNC_USER, SYNC_PASS)
    with server:
        yield server


@pytest.fixture
def sync_anki_wrapper(sync_server):
    """Create an AnkiWrapper configured to use the sync server."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")

        from anki_wrapper import AnkiWrapper
        wrapper = AnkiWrapper(collection_path)

        yield wrapper, sync_server.url

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
