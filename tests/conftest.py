"""Tests configuration."""

import os
import tempfile

import pytest


@pytest.fixture
def anki_wrapper():
    """Create a real AnkiWrapper with temporary collection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        collection_path = os.path.join(tmpdir, "test.anki21")
        media_path = collection_path + "-media"
        os.makedirs(media_path, exist_ok=True)

        from anki_wrapper import AnkiWrapper
        wrapper = AnkiWrapper(collection_path)

        yield wrapper

        wrapper.close()
