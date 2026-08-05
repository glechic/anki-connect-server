"""Tests configuration."""

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from anki_connect_server.anki_wrapper import AnkiWrapper


@pytest.fixture(autouse=True)
def isolate_test_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run each test from a clean tmp_path so the repo's .env (which may hold
    real AnkiWeb credentials) is not picked up by Config() / pydantic-settings,
    which read .env from the current working directory.
    """
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def anki_wrapper() -> Iterator[AnkiWrapper]:
    """Create a real AnkiWrapper with temporary collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = Path(tmpdir) / "test.anki21"
        media_path = collection_path.with_name(collection_path.stem + "-media")
        media_path.mkdir(parents=True, exist_ok=True)

        wrapper = AnkiWrapper(str(collection_path))

        yield wrapper

        wrapper.close()
