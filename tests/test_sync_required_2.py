"""Behavioural tests for AnkiWeb sync requirement resolution.

Covers the fix for the silent sync failure bug where required=2 (FULL_SYNC)
was unhandled, and the consolidation onto SyncCollectionResponse named
enums (FULL_SYNC / FULL_DOWNLOAD / FULL_UPLOAD / NORMAL_SYNC / NO_CHANGES)
with a structured SyncResult return.
"""

import logging
import os
import tempfile
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from anki.sync_pb2 import SyncCollectionResponse

from anki_connect_server.sync import (
    CollectionSyncOutcome,
    DownloadReason,
    SyncError,
    SyncResult,
)


@pytest.fixture
def patched_config(monkeypatch):
    """Set ANKIWEB_USER/PASS on the module-level config singleton, auto-restored."""
    from anki_connect_server.config import config

    monkeypatch.setattr(config, "ANKIWEB_USER", "test")
    monkeypatch.setattr(config, "ANKIWEB_PASS", "test")
    return config


def _mock_media_status(active: bool, checked: str = "", added: str = "", removed: str = ""):
    """Build a mock MediaSyncStatusResponse with .active and .progress counters."""
    status = Mock()
    status.active = active
    if checked or added or removed:
        progress = Mock(checked=checked, added=added, removed=removed)
        status.HasField = Mock(return_value=True)
        status.progress = progress
    else:
        status.HasField = Mock(return_value=False)
    return status


def _make_mock_col(
    required: int,
    server_media_usn: int = 0,
    *,
    new_endpoint: str = "",
    server_message: str = "",
):
    """Build a Mock Collection whose sync_collection returns `required`.

    `required` is a SyncCollectionResponse enum value (or int).
    """
    mock_col = Mock()
    mock_auth = Mock(hkey="test_key")
    mock_result = Mock()
    mock_result.required = required
    mock_result.server_media_usn = server_media_usn
    mock_result.new_endpoint = new_endpoint
    mock_result.server_message = server_message

    mock_col.sync_login = Mock(return_value=mock_auth)
    mock_col.sync_collection = Mock(return_value=mock_result)
    # media sync is now part of sync_collection(sync_media=True); wait polls
    # media_sync_status. Default: already inactive so _wait_for_media returns.
    mock_col.media_sync_status = Mock(return_value=_mock_media_status(active=False))
    mock_col.close = Mock()
    mock_col.close_for_full_sync = Mock()
    mock_col.full_upload_or_download = Mock()
    return mock_col, mock_auth, mock_result


@contextmanager
def _make_wrapper(mock_col):
    """Yield an AnkiWrapper whose Collection is `mock_col`.

    The Collection patch and temp directory stay active for the duration of
    the with-block, so _reopen_collection / _full_download (which call
    Collection(...) again) keep hitting the mock.
    """
    from anki_connect_server.anki_wrapper import AnkiWrapper

    with (
        patch("anki_connect_server.anki_wrapper.Collection", return_value=mock_col),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        collection_path = os.path.join(tmpdir, "test.anki21")
        yield AnkiWrapper(collection_path)


class TestSyncRequirementResolution:
    """SyncCollectionResponse enum values are resolved correctly."""

    def test_full_sync_downloads_with_conflict_reason(self, patched_config):
        """FULL_SYNC (the original required=2 bug) downloads and reports CONFLICT."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_SYNC, server_media_usn=42)
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        assert isinstance(result, SyncResult)
        assert result.collection.outcome is CollectionSyncOutcome.DOWNLOADED
        assert result.collection.download_reason is DownloadReason.CONFLICT
        assert result.collection.local_data_replaced is True
        mock_col.full_upload_or_download.assert_called_once()
        assert mock_col.full_upload_or_download.call_args[1]["upload"] is False

    def test_full_download_downloads_with_remote_only_reason(self, patched_config):
        """FULL_DOWNLOAD downloads and reports REMOTE_ONLY."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_DOWNLOAD, server_media_usn=42)
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        assert result.collection.outcome is CollectionSyncOutcome.DOWNLOADED
        assert result.collection.download_reason is DownloadReason.REMOTE_ONLY
        mock_col.full_upload_or_download.assert_called_once()
        assert mock_col.full_upload_or_download.call_args[1]["upload"] is False

    def test_full_upload_raises_and_preserves_local(self, patched_config):
        """FULL_UPLOAD raises SyncError by policy; local data is not uploaded."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_UPLOAD, server_media_usn=42)
        with _make_wrapper(mock_col) as wrapper:
            with pytest.raises(SyncError, match="full upload"):
                wrapper.sync_to_ankiweb()

        mock_col.full_upload_or_download.assert_not_called()
        # close_for_full_sync is not called for the upload branch
        mock_col.close_for_full_sync.assert_not_called()

    def test_normal_sync_merges(self, patched_config):
        """NORMAL_SYNC reports a merged outcome and reopens the collection."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NORMAL_SYNC)
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        assert result.collection.outcome is CollectionSyncOutcome.MERGED
        assert result.collection.local_data_replaced is False
        mock_col.full_upload_or_download.assert_not_called()

    def test_no_changes(self, patched_config):
        """NO_CHANGES reports a no_changes outcome."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NO_CHANGES)
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        assert result.collection.outcome is CollectionSyncOutcome.NO_CHANGES
        mock_col.full_upload_or_download.assert_not_called()

    def test_new_endpoint_redirect_honoured(self, patched_config):
        """A sync endpoint redirect is applied to auth.endpoint before download."""
        mock_col, mock_auth, _ = _make_mock_col(
            SyncCollectionResponse.FULL_DOWNLOAD,
            new_endpoint="https://sync2.ankiweb.net",
        )
        with _make_wrapper(mock_col) as wrapper:
            wrapper.sync_to_ankiweb()

        assert mock_auth.endpoint == "https://sync2.ankiweb.net"

    def test_server_message_propagated(self, patched_config):
        """server_message from the sync response is surfaced in SyncResult."""
        mock_col, _, _ = _make_mock_col(
            SyncCollectionResponse.NO_CHANGES, server_message="hello from server"
        )
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        assert result.server_message == "hello from server"


class TestSyncSafety:
    """Concurrency, failure recovery, and abort behaviour."""

    def test_concurrent_sync_rejected(self, patched_config):
        """A second sync while one is in progress raises SyncError."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NO_CHANGES)
        with _make_wrapper(mock_col) as wrapper:
            assert wrapper._sync_lock.acquire(blocking=False) is True  # type: ignore[private-usage]
            try:
                with pytest.raises(SyncError, match="already in progress"):
                    wrapper.sync_to_ankiweb()
            finally:
                wrapper._sync_lock.release()  # type: ignore[private-usage]

            # After release, sync works again.
            wrapper.sync_to_ankiweb()

    def test_full_download_failure_raises_sync_error(self, patched_config):
        """If the download fails, a SyncError is raised (not the raw exception)."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_DOWNLOAD)
        mock_col.full_upload_or_download = Mock(side_effect=RuntimeError("network died"))
        with _make_wrapper(mock_col) as wrapper:
            with pytest.raises(SyncError, match="Full collection download failed"):
                wrapper.sync_to_ankiweb()

    def test_sync_collection_failure_raises_sync_error(self, patched_config):
        """If sync_collection itself fails, SyncError is raised and col is closed."""
        mock_col = Mock()
        mock_auth = Mock(hkey="test_key")
        mock_col.sync_login = Mock(return_value=mock_auth)
        mock_col.sync_collection = Mock(side_effect=RuntimeError("auth server down"))
        mock_col.close = Mock()
        mock_col.media_sync_status = Mock(return_value=_mock_media_status(active=False))
        with _make_wrapper(mock_col) as wrapper:
            with pytest.raises(SyncError, match="Collection synchronization failed"):
                wrapper.sync_to_ankiweb()

        mock_col.close.assert_called()

    def test_abort_sync_calls_both_abort_methods(self):
        """abort_sync calls col.abort_sync and col.abort_media_sync."""
        mock_col = Mock()
        with _make_wrapper(mock_col) as wrapper:
            wrapper.abort_sync()

        mock_col.abort_sync.assert_called_once()
        mock_col.abort_media_sync.assert_called_once()

    def test_abort_sync_swallows_errors(self):
        """abort_sync must not raise even if the underlying abort methods fail."""
        mock_col = Mock()
        mock_col.abort_sync = Mock(side_effect=RuntimeError("boom"))
        mock_col.abort_media_sync = Mock(side_effect=RuntimeError("boom2"))
        with _make_wrapper(mock_col) as wrapper:
            # Must not raise.
            wrapper.abort_sync()

        mock_col.abort_sync.assert_called_once()
        mock_col.abort_media_sync.assert_called_once()

    def test_error_logged_on_failure(self, patched_config, caplog):
        """Errors during sync are logged with the exception."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_DOWNLOAD)
        mock_col.full_upload_or_download = Mock(side_effect=ValueError("Test error"))
        with _make_wrapper(mock_col) as wrapper:
            with caplog.at_level(logging.ERROR):
                with pytest.raises(SyncError, match="Full collection download failed"):
                    wrapper.sync_to_ankiweb()

        assert "Test error" in caplog.text


class TestCollectionGeneration:
    """collection_generation increments whenever sync reopens the collection.

    Callers (e.g. a future review session) can use this to detect that a sync
    invalidated their cached card/note handles mid-session.
    """

    def test_starts_at_zero(self):
        """A fresh wrapper has collection_generation == 0."""
        mock_col = Mock()
        with _make_wrapper(mock_col) as wrapper:
            assert wrapper.collection_generation == 0

    def test_full_sync_increments(self, patched_config):
        """FULL_SYNC reopens via _full_download -> _reopen_collection (+1)."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_SYNC)
        with _make_wrapper(mock_col) as wrapper:
            assert wrapper.collection_generation == 0
            wrapper.sync_to_ankiweb()

        assert wrapper.collection_generation == 1

    def test_full_download_increments(self, patched_config):
        """FULL_DOWNLOAD reopens via _full_download -> _reopen_collection (+1)."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_DOWNLOAD)
        with _make_wrapper(mock_col) as wrapper:
            assert wrapper.collection_generation == 0
            wrapper.sync_to_ankiweb()

        assert wrapper.collection_generation == 1

    def test_normal_sync_increments(self, patched_config):
        """NORMAL_SYNC reopens after media sync (+1)."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NORMAL_SYNC)
        with _make_wrapper(mock_col) as wrapper:
            wrapper.sync_to_ankiweb()

        assert wrapper.collection_generation == 1

    def test_no_changes_increments(self, patched_config):
        """NO_CHANGES reopens after media sync (+1)."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NO_CHANGES)
        with _make_wrapper(mock_col) as wrapper:
            wrapper.sync_to_ankiweb()

        assert wrapper.collection_generation == 1

    def test_full_upload_does_not_increment(self, patched_config):
        """FULL_UPLOAD raises before any reopen, so generation stays at 0."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_UPLOAD)
        with _make_wrapper(mock_col) as wrapper:
            with pytest.raises(SyncError, match="full upload"):
                wrapper.sync_to_ankiweb()

        assert wrapper.collection_generation == 0

    def test_repeated_syncs_accumulate(self, patched_config):
        """Each successful sync increments the generation by 1."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NO_CHANGES)
        with _make_wrapper(mock_col) as wrapper:
            wrapper.sync_to_ankiweb()
            assert wrapper.collection_generation == 1
            wrapper.sync_to_ankiweb()
            assert wrapper.collection_generation == 2
            wrapper.sync_to_ankiweb()
            assert wrapper.collection_generation == 3

    def test_failed_download_still_increments(self, patched_config):
        """_full_download reopens in a finally, so even a failed download
        increments generation (the collection is reopened to a usable state)."""
        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.FULL_DOWNLOAD)
        mock_col.full_upload_or_download = Mock(side_effect=RuntimeError("network died"))
        with _make_wrapper(mock_col) as wrapper:
            with pytest.raises(SyncError, match="Full collection download failed"):
                wrapper.sync_to_ankiweb()

        # _full_download's finally called _reopen_collection before the
        # SyncError wrapper raised, so generation advanced.
        assert wrapper.collection_generation == 1


class TestMediaSync:
    """sync_media_only and _wait_for_media behaviour."""

    def test_sync_media_only_waits_for_completion(self, patched_config):
        """sync_media_only polls media_sync_status until inactive and returns counters."""
        mock_col = Mock()
        mock_auth = Mock(hkey="test_key")
        # First poll: active. Second poll: inactive with counters.
        mock_col.media_sync_status = Mock(
            side_effect=[
                _mock_media_status(active=True, checked="5", added="2", removed="1"),
                _mock_media_status(active=False, checked="5", added="2", removed="1"),
            ]
        )
        mock_col.sync_login = Mock(return_value=mock_auth)
        mock_col.sync_media = Mock()
        mock_col.abort_sync = Mock()
        mock_col.abort_media_sync = Mock()
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_media_only()

        assert result.outcome == "completed"
        assert result.checked == "5"
        assert result.added == "2"
        assert result.removed == "1"
        mock_col.sync_media.assert_called_once_with(mock_auth)
        assert mock_col.media_sync_status.call_count == 2
        mock_col.abort_sync.assert_not_called()

    def test_sync_media_only_aborts_on_timeout(self, patched_config):
        """sync_media_only aborts and raises SyncError when media sync never finishes."""
        mock_col = Mock()
        mock_auth = Mock(hkey="test_key")
        mock_col.sync_login = Mock(return_value=mock_auth)
        mock_col.sync_media = Mock()
        mock_col.media_sync_status = Mock(return_value=_mock_media_status(active=True))
        mock_col.abort_sync = Mock()
        mock_col.abort_media_sync = Mock()
        with _make_wrapper(mock_col) as wrapper:
            with pytest.raises(SyncError, match="media sync timed out"):
                wrapper.sync_media_only(timeout=0.05, poll_interval=0.01)

        mock_col.abort_sync.assert_called_once()
        mock_col.abort_media_sync.assert_called_once()

    def test_sync_media_only_rejects_concurrent(self, patched_config):
        """A second media sync while one is in progress raises SyncError."""
        mock_col = Mock()
        mock_auth = Mock(hkey="test_key")
        mock_col.sync_login = Mock(return_value=mock_auth)
        mock_col.sync_media = Mock()
        mock_col.media_sync_status = Mock(return_value=_mock_media_status(active=False))
        with _make_wrapper(mock_col) as wrapper:
            assert wrapper._sync_lock.acquire(blocking=False) is True  # type: ignore[private-usage]
            try:
                with pytest.raises(SyncError, match="already in progress"):
                    wrapper.sync_media_only()
            finally:
                wrapper._sync_lock.release()  # type: ignore[private-usage]


class TestSyncResultStructure:
    """SyncResult is a structured Pydantic model, not a string."""

    def test_result_is_pydantic_model(self, patched_config):
        from pydantic import BaseModel

        mock_col, _, _ = _make_mock_col(SyncCollectionResponse.NO_CHANGES)
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        assert isinstance(result, BaseModel)
        assert result.status == "completed"

    def test_result_serialises_to_json(self, patched_config):
        """SyncResult can be serialised to JSON for the REST/MCP response."""
        mock_col, _, _ = _make_mock_col(
            SyncCollectionResponse.FULL_SYNC, server_message="redirected"
        )
        with _make_wrapper(mock_col) as wrapper:
            result = wrapper.sync_to_ankiweb()

        dumped = result.model_dump(mode="json", exclude_none=True)
        assert dumped["status"] == "completed"
        assert dumped["collection"]["outcome"] == "downloaded"
        assert dumped["collection"]["download_reason"] == "conflict"
        assert dumped["server_message"] == "redirected"
