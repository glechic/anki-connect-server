"""Tests configuration."""

import os
import tempfile

import pytest

os.environ["ANKICONNECT_COLLECTION_PATH"] = "/tmp/test_collection.anki21"


@pytest.fixture
def anki_wrapper():
    """Create a real AnkiWrapper with temporary collection."""
    with tempfile.NamedTemporaryFile(suffix=".anki21", delete=False) as f:
        collection_path = f.name

    from anki_wrapper import AnkiWrapper
    wrapper = AnkiWrapper(collection_path)

    yield wrapper

    wrapper.close()
    if os.path.exists(collection_path):
        os.remove(collection_path)
