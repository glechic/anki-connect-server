"""Tests configuration."""

import os
import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolate_test_working_directory(monkeypatch, tmp_path):
    """Run each test from a clean tmp_path so the repo's .env (which may hold
    real AnkiWeb credentials) is not picked up by Config() / pydantic-settings,
    which read .env from the current working directory.
    """
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def anki_wrapper():
    """Create a real AnkiWrapper with temporary collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")
        media_path = collection_path + "-media"
        os.makedirs(media_path, exist_ok=True)

        from anki_connect_server.anki_wrapper import AnkiWrapper

        wrapper = AnkiWrapper(collection_path)

        yield wrapper

        wrapper.close()