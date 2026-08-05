"""Typed synchronization results.

Models the outcome of an AnkiWeb sync so callers (REST handlers, MCP tools)
get a structured result instead of a string, and so the
``SyncCollectionResponse`` requirement is resolved via named enums rather
than magic integers.

Adapted from friedrich-de's fork; the MCP ``SyncManager`` foreground
orchestration is omitted here (we don't wire sync progress to an MCP
Context yet).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CollectionSyncOutcome(StrEnum):
    NO_CHANGES = "no_changes"
    MERGED = "merged"
    DOWNLOADED = "downloaded"


class DownloadReason(StrEnum):
    """Why a full download was performed."""

    CONFLICT = "conflict"
    REMOTE_ONLY = "remote_only"


class CollectionSyncResult(_StrictModel):
    outcome: CollectionSyncOutcome
    download_reason: DownloadReason | None = None
    local_data_replaced: bool


class MediaSyncResult(_StrictModel):
    outcome: Literal["completed"] = "completed"
    checked: str | None = None
    added: str | None = None
    removed: str | None = None


class SyncResult(_StrictModel):
    status: Literal["completed"] = "completed"
    collection: CollectionSyncResult
    media: MediaSyncResult
    server_message: str | None = None


class SyncError(RuntimeError):
    """Raised when a synchronization phase cannot complete safely."""
