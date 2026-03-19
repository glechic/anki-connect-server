"""Tests for config module."""

import os
import pytest
from unittest.mock import patch
import importlib


def reload_config():
    """Reload config module to pick up new env vars."""
    import config
    importlib.reload(config)
    return config


class TestConfig:
    """Test configuration module."""

    def test_default_config(self):
        """Test default configuration values."""
        with patch.dict(os.environ, {"ANKI_COLLECTION_PATH": "/test/path.anki21"}):
            cfg = reload_config()
            assert cfg.config.PORT == 8765
            assert cfg.config.BIND == "127.0.0.1"
            assert cfg.config.COLLECTION_PATH == "/test/path.anki21"

    def test_custom_port(self):
        """Test custom port configuration."""
        with patch.dict(os.environ, {
            "ANKI_COLLECTION_PATH": "/test/path.anki21",
            "ANKICONNECT_PORT": "9000"
        }):
            cfg = reload_config()
            assert cfg.config.PORT == 9000

    def test_custom_bind(self):
        """Test custom bind address configuration."""
        with patch.dict(os.environ, {
            "ANKI_COLLECTION_PATH": "/test/path.anki21",
            "ANKICONNECT_BIND": "0.0.0.0"
        }):
            cfg = reload_config()
            assert cfg.config.BIND == "0.0.0.0"

    def test_ankiweb_config(self):
        """Test AnkiWeb configuration."""
        with patch.dict(os.environ, {
            "ANKI_COLLECTION_PATH": "/test/path.anki21",
            "ANKICONNECT_ANKIWEB_USER": "test@example.com",
            "ANKICONNECT_ANKIWEB_PASS": "password123"
        }):
            cfg = reload_config()
            assert cfg.config.ANKIWEB_USER == "test@example.com"
            assert cfg.config.ANKIWEB_PASS == "password123"

    def test_ankiweb_url_config(self):
        """Test custom sync server URL."""
        with patch.dict(os.environ, {
            "ANKI_COLLECTION_PATH": "/test/path.anki21",
            "ANKIWEB_URL": "https://sync.myserver.com"
        }):
            cfg = reload_config()
            assert cfg.config.ANKIWEB_URL == "https://sync.myserver.com"

    def test_validate_raises_without_collection_path(self):
        """Test that validation raises error without collection path."""
        with patch.dict(os.environ, {}, clear=True):
            cfg = reload_config()
            with pytest.raises(ValueError, match="ANKI_COLLECTION_PATH"):
                cfg.Config.validate()

    def test_validate_passes_with_collection_path(self):
        """Test that validation passes with collection path."""
        with patch.dict(os.environ, {"ANKI_COLLECTION_PATH": "/test/path.anki21"}):
            cfg = reload_config()
            cfg.Config.validate()

    def test_optional_ankiweb_config(self):
        """Test that AnkiWeb config is optional."""
        with patch.dict(os.environ, {"ANKI_COLLECTION_PATH": "/test/path.anki21"}):
            cfg = reload_config()
            assert cfg.config.ANKIWEB_USER is None
            assert cfg.config.ANKIWEB_PASS is None