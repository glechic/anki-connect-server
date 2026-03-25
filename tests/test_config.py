"""Tests for config module."""

import pytest


def test_config_defaults():
    """Test that config has correct defaults."""
    from anki_connect_server.config import Config
    cfg = Config(COLLECTION_PATH="/test/path.anki21")
    assert cfg.PORT == 8765
    assert cfg.BIND == "127.0.0.1"


def test_config_custom_values():
    """Test custom configuration values."""
    from anki_connect_server.config import Config
    cfg = Config(
        PORT=9000,
        BIND="0.0.0.0",
        COLLECTION_PATH="/test/path.anki21"
    )
    assert cfg.PORT == 9000
    assert cfg.BIND == "0.0.0.0"


def test_config_ankiweb():
    """Test AnkiWeb configuration."""
    from anki_connect_server.config import Config
    cfg = Config(
        COLLECTION_PATH="/test/path.anki21",
        ANKIWEB_USER="test@example.com",
        ANKIWEB_PASS="password123"
    )
    assert cfg.ANKIWEB_USER == "test@example.com"
    assert cfg.ANKIWEB_PASS == "password123"


def test_config_optional_ankiweb(monkeypatch):
    """Test that AnkiWeb config is optional when not set in env."""
    from anki_connect_server.config import Config
    monkeypatch.setenv("ANKICONNECT_COLLECTION_PATH", "/test/path.anki21")
    monkeypatch.delenv("ANKICONNECT_ANKIWEB_USER", raising=False)
    monkeypatch.delenv("ANKICONNECT_ANKIWEB_PASS", raising=False)
    
    cfg = Config(_env_file=None)
    assert cfg.ANKIWEB_USER is None
    assert cfg.ANKIWEB_PASS is None


def test_validate_passes_with_collection_path():
    """Test that validation passes with collection path."""
    from anki_connect_server.config import Config
    cfg = Config(COLLECTION_PATH="/test/path.anki21")
    assert cfg.COLLECTION_PATH == "/test/path.anki21"


def test_config_loads_from_env(monkeypatch):
    """Test that config loads from environment variables."""
    monkeypatch.setenv("ANKICONNECT_COLLECTION_PATH", "/env/path.anki21")
    monkeypatch.setenv("ANKICONNECT_PORT", "9000")
    monkeypatch.setenv("ANKICONNECT_ANKIWEB_USER", "env@user.com")
    monkeypatch.setenv("ANKICONNECT_ANKIWEB_URL", "https://sync.example.com")
    
    import importlib
    import anki_connect_server.config as config
    importlib.reload(config)
    
    assert config.config.PORT == 9000
    assert config.config.COLLECTION_PATH == "/env/path.anki21"
    assert config.config.ANKIWEB_USER == "env@user.com"
    assert config.config.ANKIWEB_URL == "https://sync.example.com"