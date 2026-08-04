"""Behavioral tests for required=2 (FULL_SYNC) handling.

This test verifies the fix for the silent sync failure bug where:
- sync() returned "sync completed" but data didn't upload
- required=2 (FULL_SYNC) was not handled, causing silent failures
"""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def patched_config(monkeypatch):
    """Set ANKIWEB_USER/PASS on the module-level config singleton, auto-restored.

    Uses monkeypatch so a test that crashes mid-assertion cannot leak credentials
    or FULL_UPLOAD state into subsequent tests (the original try/finally pattern
    was racy under test failures).
    """
    from anki_connect_server.config import config

    monkeypatch.setattr(config, "ANKIWEB_USER", "test")
    monkeypatch.setattr(config, "ANKIWEB_PASS", "test")
    # Default FULL_UPLOAD to False; individual tests that need True should call
    # monkeypatch.setattr(config, "FULL_UPLOAD", True) themselves so it is
    # auto-restored.
    monkeypatch.setattr(config, "FULL_UPLOAD", False)
    return config


def _make_mock_col(required: int, host_number: int = 7, server_media_usn: int = 0):
    """Build a Mock Collection with the given sync_collection result."""
    mock_col = Mock()
    mock_auth = Mock(hkey="test_key")
    mock_result = Mock()
    mock_result.required = required
    mock_result.host_number = host_number
    mock_result.server_media_usn = server_media_usn

    mock_col.sync_login = Mock(return_value=mock_auth)
    mock_col.sync_collection = Mock(return_value=mock_result)
    mock_col.close = Mock()
    mock_col.close_for_full_sync = Mock()
    mock_col.full_upload_or_download = Mock()
    return mock_col, mock_auth, mock_result


class TestRequired2Behavior:
    """Test that required=2 (FULL_SYNC) downloads from AnkiWeb."""

    def test_required_2_downloads_from_ankiweb(self, patched_config, monkeypatch):
        """required=2 triggers download from AnkiWeb (not upload).

        This is the main bug fix: previously required=2 was unhandled and sync
        reported success without actually syncing.
        """
        monkeypatch.setattr(patched_config, "FULL_UPLOAD", False)
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=2, server_media_usn=12345)

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                result = wrapper.sync_to_ankiweb()

            assert "sync completed" in result
            assert "required=2" in result

            mock_col.full_upload_or_download.assert_called_once()
            call_args = mock_col.full_upload_or_download.call_args
            assert call_args[1]["upload"] is False, (
                "required=2 must DOWNLOAD from AnkiWeb (upload=False), not upload"
            )

    def test_required_3_downloads_from_ankiweb(self, patched_config):
        """required=3 (FULL_DOWNLOAD) downloads from AnkiWeb."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=3, server_media_usn=12345)

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                result = wrapper.sync_to_ankiweb()

            assert "sync completed" in result
            mock_col.full_upload_or_download.assert_called_once()
            assert mock_col.full_upload_or_download.call_args[1]["upload"] is False

    def test_required_4_uploads_with_config(self, patched_config, monkeypatch):
        """required=4 (FULL_UPLOAD) uploads when FULL_UPLOAD=true."""
        monkeypatch.setattr(patched_config, "FULL_UPLOAD", True)
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=4, server_media_usn=12345)

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                result = wrapper.sync_to_ankiweb()

            assert "sync completed" in result
            mock_col.full_upload_or_download.assert_called_once()
            assert mock_col.full_upload_or_download.call_args[1]["upload"] is True

    def test_required_4_skips_without_config(self, patched_config, caplog, monkeypatch):
        """required=4 is skipped (with a warning) when FULL_UPLOAD=false."""
        import logging

        monkeypatch.setattr(patched_config, "FULL_UPLOAD", False)
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=4)

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                with caplog.at_level(logging.WARNING):
                    result = wrapper.sync_to_ankiweb()

            assert "sync completed" in result
            mock_col.full_upload_or_download.assert_not_called()
            assert "FULL_UPLOAD=false" in caplog.text

    def test_sync_failure_after_close_for_full_sync_keeps_wrapper_consistent(self, patched_config):
        """If reopen after sync failure also fails, the closed handle is left in place
        (no corrupted Collection is constructed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=3)

            # The download itself fails.
            mock_col.full_upload_or_download = Mock(side_effect=RuntimeError("network died"))

            with patch(
                "anki_connect_server.anki_wrapper.Collection", return_value=mock_col
            ) as col_factory:
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)

                # Patch Collection so the reopen also fails.
                col_factory.side_effect = RuntimeError("disk on fire")
                with pytest.raises(RuntimeError, match="network died"):
                    wrapper.sync_to_ankiweb()

                # The original exception propagates; self.col still points at the
                # closed handle, not a freshly-opened Collection (which would
                # serve corrupted data). col_factory.side_effect is set, so no
                # new Collection was constructed.
                assert wrapper.col is mock_col

    def test_sync_failure_without_close_for_full_sync_preserves_handle(self, patched_config):
        """If close_for_full_sync was never called, the original col handle is left intact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            mock_auth = Mock(hkey="test_key")
            # sync_collection itself raises (network issue before any close).
            mock_col.sync_login = Mock(return_value=mock_auth)
            mock_col.sync_collection = Mock(side_effect=RuntimeError("auth server down"))

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)

                with pytest.raises(RuntimeError, match="auth server down"):
                    wrapper.sync_to_ankiweb()

                # Handle untouched; close_for_full_sync not called.
                assert wrapper.col is mock_col

    def test_sync_media_only_waits_for_completion(self, patched_config):
        """sync_media_only polls media_sync_status until running=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            mock_auth = Mock(hkey="test_key")

            # First poll: still running. Second poll: done.
            status_running = Mock(running=True)
            status_done = Mock(running=False)
            mock_col.media_sync_status = Mock(side_effect=[status_running, status_done])

            mock_col.sync_login = Mock(return_value=mock_auth)
            mock_col.sync_media = Mock()
            mock_col.abort_sync = Mock()
            mock_col.abort_media_sync = Mock()

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                result = wrapper.sync_media_only()

            assert result == "media sync completed"
            mock_col.sync_media.assert_called_once_with(mock_auth)
            # Polled until running=False.
            assert mock_col.media_sync_status.call_count == 2
            # Did not abort since it finished in time.
            mock_col.abort_sync.assert_not_called()

    def test_sync_media_only_aborts_on_timeout(self, patched_config):
        """sync_media_only aborts and raises SyncError when media sync never finishes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            mock_auth = Mock(hkey="test_key")
            mock_col.sync_login = Mock(return_value=mock_auth)
            mock_col.sync_media = Mock()
            mock_col.media_sync_status = Mock(return_value=Mock(running=True))
            mock_col.abort_sync = Mock()
            mock_col.abort_media_sync = Mock()

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper, SyncError

                wrapper = AnkiWrapper(collection_path)

                with pytest.raises(SyncError, match="media sync timed out"):
                    wrapper.sync_media_only(timeout=0.05, poll_interval=0.01)

                mock_col.abort_sync.assert_called_once()
                mock_col.abort_media_sync.assert_called_once()

    def test_concurrent_sync_rejected(self, patched_config):
        """A second sync while one is in progress must raise SyncError, not corrupt state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=0)

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper, SyncError

                wrapper = AnkiWrapper(collection_path)

                # Acquire the lock manually to simulate an in-progress sync.
                assert wrapper._sync_lock.acquire(blocking=False) is True
                try:
                    with pytest.raises(SyncError, match="already in progress"):
                        wrapper.sync_to_ankiweb()
                finally:
                    wrapper._sync_lock.release()

                # After release, sync must work again.
                mock_col.full_upload_or_download.reset_mock()
                wrapper.sync_to_ankiweb()
                mock_col.full_upload_or_download.assert_not_called()

    def test_abort_sync_calls_both_abort_methods(self):
        """abort_sync calls col.abort_sync and col.abort_media_sync."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                wrapper.abort_sync()

            mock_col.abort_sync.assert_called_once()
            mock_col.abort_media_sync.assert_called_once()

    def test_abort_sync_swallows_errors(self):
        """abort_sync must not raise even if the underlying abort methods fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            mock_col.abort_sync = Mock(side_effect=RuntimeError("boom"))
            mock_col.abort_media_sync = Mock(side_effect=RuntimeError("boom2"))
            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)
                # Must not raise.
                wrapper.abort_sync()

            mock_col.abort_sync.assert_called_once()
            mock_col.abort_media_sync.assert_called_once()

    def test_error_shows_exception_type(self, patched_config, caplog):
        """Errors logged during sync include the exception type, not just the message."""
        import logging

        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")
            mock_col, _mock_auth, _ = _make_mock_col(required=3)
            mock_col.full_upload_or_download = Mock(side_effect=ValueError("Test error"))

            with patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper

                wrapper = AnkiWrapper(collection_path)

                with caplog.at_level(logging.ERROR):
                    with pytest.raises(ValueError, match="Test error"):
                        wrapper.sync_to_ankiweb()

                # Verify error log includes exception type.
                assert "ValueError" in caplog.text
                assert "Test error" in caplog.text
