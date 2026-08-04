"""Behavioral tests for required=2 (FULL_SYNC) handling.

This test verifies the fix for the silent sync failure bug where:
- sync() returned "sync completed" but data didn't upload
- required=2 (FULL_SYNC) was not handled, causing silent failures
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import os


class TestRequired2Behavior:
    """Test that required=2 (FULL_SYNC) downloads from AnkiWeb."""

    def test_required_2_downloads_from_ankiweb(self, caplog):
        """Test that required=2 triggers download from AnkiWeb (not upload).
        
        This is the main bug fix - previously required=2 was not handled
        and sync would report success without actually syncing.
        """
        import logging
        from anki_connect_server.config import config

        original_upload = config.FULL_UPLOAD
        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS

        config.FULL_UPLOAD = False
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                # Create mock collection
                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_result = Mock()
                mock_result.required = 2
                mock_result.host_number = 7
                mock_result.server_media_usn = 12345

                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_collection = Mock(return_value=mock_result)
                mock_col.close = Mock()
                mock_col.close_for_full_sync = Mock()
                mock_col.full_upload_or_download = Mock()

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper
                    wrapper = AnkiWrapper(collection_path)

                    result = wrapper.sync_to_ankiweb()

                    # Verify sync completed
                    assert "sync completed" in result
                    assert "required=2" in result

                    # KEY ASSERTION: required=2 should DOWNLOAD (upload=False), not upload
                    mock_col.full_upload_or_download.assert_called_once()
                    call_args = mock_col.full_upload_or_download.call_args
                    assert call_args[1]["upload"] is False, \
                        "required=2 must DOWNLOAD from AnkiWeb (upload=False), not upload"

        finally:
            config.FULL_UPLOAD = original_upload
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_required_3_downloads_from_ankiweb(self):
        """Test that required=3 (FULL_DOWNLOAD) downloads from AnkiWeb."""
        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_result = Mock()
                mock_result.required = 3
                mock_result.host_number = 7
                mock_result.server_media_usn = 12345

                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_collection = Mock(return_value=mock_result)
                mock_col.close = Mock()
                mock_col.close_for_full_sync = Mock()
                mock_col.full_upload_or_download = Mock()

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper
                    wrapper = AnkiWrapper(collection_path)

                    result = wrapper.sync_to_ankiweb()

                    assert "sync completed" in result

                    # Verify download (upload=False)
                    mock_col.full_upload_or_download.assert_called_once()
                    call_args = mock_col.full_upload_or_download.call_args
                    assert call_args[1]["upload"] is False

        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_required_4_uploads_with_config(self):
        """Test that required=4 (FULL_UPLOAD) uploads when FULL_UPLOAD=true."""
        from anki_connect_server.config import config

        original_upload = config.FULL_UPLOAD
        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS

        config.FULL_UPLOAD = True
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_result = Mock()
                mock_result.required = 4
                mock_result.host_number = 7
                mock_result.server_media_usn = 12345

                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_collection = Mock(return_value=mock_result)
                mock_col.close = Mock()
                mock_col.close_for_full_sync = Mock()
                mock_col.full_upload_or_download = Mock()

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper
                    wrapper = AnkiWrapper(collection_path)

                    result = wrapper.sync_to_ankiweb()

                    assert "sync completed" in result

                    # Verify upload (upload=True)
                    mock_col.full_upload_or_download.assert_called_once()
                    call_args = mock_col.full_upload_or_download.call_args
                    assert call_args[1]["upload"] is True

        finally:
            config.FULL_UPLOAD = original_upload
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_required_4_skips_without_config(self, caplog):
        """Test that required=4 is skipped when FULL_UPLOAD=false."""
        import logging
        from anki_connect_server.config import config

        original_upload = config.FULL_UPLOAD
        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS

        config.FULL_UPLOAD = False
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_result = Mock()
                mock_result.required = 4
                mock_result.host_number = 7

                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_collection = Mock(return_value=mock_result)
                mock_col.close = Mock()

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper
                    wrapper = AnkiWrapper(collection_path)

                    with caplog.at_level(logging.WARNING):
                        result = wrapper.sync_to_ankiweb()

                    assert "sync completed" in result

                    # Should NOT call full_upload_or_download
                    mock_col.full_upload_or_download.assert_not_called()

                    # Should log warning
                    assert "FULL_UPLOAD=false" in caplog.text

        finally:
            config.FULL_UPLOAD = original_upload
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_sync_media_only_waits_for_completion(self):
        """sync_media_only must poll media_sync_status until running=False."""
        import tempfile
        import os
        from unittest.mock import Mock, patch, call

        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
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

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper
                    wrapper = AnkiWrapper(collection_path)

                    result = wrapper.sync_media_only()
                    assert result == "media sync completed"

                    mock_col.sync_media.assert_called_once_with(mock_auth)
                    # Polled until running=False
                    assert mock_col.media_sync_status.call_count == 2
                    # Did not abort since it finished in time
                    mock_col.abort_sync.assert_not_called()
        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_sync_media_only_aborts_on_timeout(self):
        """sync_media_only must abort and raise SyncError when media sync never finishes."""
        import tempfile
        import os
        from unittest.mock import Mock, patch

        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_media = Mock()
                mock_col.media_sync_status = Mock(return_value=Mock(running=True))
                mock_col.abort_sync = Mock()
                mock_col.abort_media_sync = Mock()

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper, SyncError
                    wrapper = AnkiWrapper(collection_path)

                    with pytest.raises(SyncError, match="media sync timed out"):
                        wrapper.sync_media_only(timeout=0.05, poll_interval=0.01)

                    mock_col.abort_sync.assert_called_once()
                    mock_col.abort_media_sync.assert_called_once()
        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_concurrent_sync_rejected(self):
        """A second sync while one is in progress must raise SyncError, not corrupt state."""
        import tempfile
        import os
        from unittest.mock import Mock, patch

        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_result = Mock()
                mock_result.required = 0
                mock_result.host_number = 7
                mock_result.server_media_usn = 0

                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_collection = Mock(return_value=mock_result)
                mock_col.close = Mock()
                mock_col.full_upload_or_download = Mock()

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
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
        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass

    def test_abort_sync_calls_both_abort_methods(self):
        """abort_sync must call col.abort_sync and col.abort_media_sync."""
        import tempfile
        import os
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper
                wrapper = AnkiWrapper(collection_path)

                wrapper.abort_sync()
                mock_col.abort_sync.assert_called_once()
                mock_col.abort_media_sync.assert_called_once()

    def test_abort_sync_swallows_errors(self):
        """abort_sync must not raise even if the underlying abort methods fail."""
        import tempfile
        import os
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as tmpdir:
            collection_path = os.path.join(tmpdir, "test.anki21")

            mock_col = Mock()
            mock_col.abort_sync = Mock(side_effect=RuntimeError("boom"))
            mock_col.abort_media_sync = Mock(side_effect=RuntimeError("boom2"))
            with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                from anki_connect_server.anki_wrapper import AnkiWrapper
                wrapper = AnkiWrapper(collection_path)

                # Must not raise.
                wrapper.abort_sync()
                mock_col.abort_sync.assert_called_once()
                mock_col.abort_media_sync.assert_called_once()

    def test_error_shows_exception_type(self, caplog):
        """Test that errors include exception type, not just message."""
        import logging
        from anki_connect_server.config import config

        original_user = config.ANKIWEB_USER
        original_pass = config.ANKIWEB_PASS
        config.ANKIWEB_USER = "test"
        config.ANKIWEB_PASS = "test"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                collection_path = os.path.join(tmpdir, "test.anki21")

                mock_col = Mock()
                mock_auth = Mock(hkey="test_key")
                mock_result = Mock()
                mock_result.required = 0

                mock_col.sync_login = Mock(return_value=mock_auth)
                mock_col.sync_collection = Mock(return_value=mock_result)
                mock_col.close = Mock(side_effect=ValueError("Test error"))

                with patch('anki_connect_server.anki_wrapper.Collection', return_value=mock_col):
                    from anki_connect_server.anki_wrapper import AnkiWrapper
                    wrapper = AnkiWrapper(collection_path)

                    with caplog.at_level(logging.ERROR):
                        with pytest.raises(ValueError, match="Test error"):
                            wrapper.sync_to_ankiweb()

                    # Verify error log includes exception type
                    assert "ValueError" in caplog.text
                    assert "Test error" in caplog.text

        finally:
            config.ANKIWEB_USER = original_user
            config.ANKIWEB_PASS = original_pass
