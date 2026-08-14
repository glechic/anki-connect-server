"""Tests for config module."""


def test_config_defaults():
    """Test that config has correct defaults."""
    from anki_connect_server.config import Config

    cfg = Config(COLLECTION_PATH="/test/path.anki2")
    assert cfg.PORT == 8765
    assert cfg.BIND == "127.0.0.1"


def test_config_custom_values():
    """Test custom configuration values."""
    from anki_connect_server.config import Config

    cfg = Config(PORT=9000, BIND="0.0.0.0", COLLECTION_PATH="/test/path.anki2")
    assert cfg.PORT == 9000
    assert cfg.BIND == "0.0.0.0"


def test_config_ankiweb():
    """Test AnkiWeb configuration."""
    from anki_connect_server.config import Config

    cfg = Config(
        COLLECTION_PATH="/test/path.anki2",
        ANKIWEB_USER="test@example.com",
        ANKIWEB_PASS="password123",
    )
    assert cfg.ANKIWEB_USER == "test@example.com"
    assert cfg.ANKIWEB_PASS == "password123"


def test_config_optional_ankiweb(monkeypatch):
    """Test that AnkiWeb config is optional when not set in env."""
    from anki_connect_server.config import Config

    monkeypatch.setenv("ANKICONNECT_COLLECTION_PATH", "/test/path.anki2")
    monkeypatch.delenv("ANKICONNECT_ANKIWEB_USER", raising=False)
    monkeypatch.delenv("ANKICONNECT_ANKIWEB_PASS", raising=False)

    cfg = Config(_env_file=None)  # type: ignore[call-arg]
    assert cfg.ANKIWEB_USER is None
    assert cfg.ANKIWEB_PASS is None


def test_validate_passes_with_collection_path():
    """Test that validation passes with collection path."""
    from anki_connect_server.config import Config

    cfg = Config(COLLECTION_PATH="/test/path.anki2")
    assert cfg.COLLECTION_PATH == "/test/path.anki2"


def test_config_loads_from_env(monkeypatch):
    """Config reads ANKICONNECT_* env vars.

    Construct a fresh Config() (not the cached singleton) so the test does not
    need importlib.reload, which would corrupt the @cache'd get_config() for
    the rest of the test session (other modules hold a reference to the
    pre-reload instance).
    """
    monkeypatch.setenv("ANKICONNECT_COLLECTION_PATH", "/env/path.anki2")
    monkeypatch.setenv("ANKICONNECT_PORT", "9000")
    monkeypatch.setenv("ANKICONNECT_ANKIWEB_USER", "env@user.com")
    monkeypatch.setenv("ANKICONNECT_ANKIWEB_URL", "https://sync.example.com")

    from anki_connect_server.config import Config

    cfg = Config(_env_file=None)  # type: ignore[call-arg]
    assert cfg.PORT == 9000
    assert cfg.COLLECTION_PATH == "/env/path.anki2"
    assert cfg.ANKIWEB_USER == "env@user.com"
    assert cfg.ANKIWEB_URL == "https://sync.example.com"


def test_config_defaults_empty_collection_path_to_temp():
    """An empty COLLECTION_PATH defaults to a temp path instead of raising."""
    from anki_connect_server.config import Config

    cfg = Config(COLLECTION_PATH="", _env_file=None)  # type: ignore[call-arg]
    assert cfg.COLLECTION_PATH != ""
    assert cfg.COLLECTION_PATH.endswith("collection.anki2")
    assert "anki-connect-server" in cfg.COLLECTION_PATH


def test_config_accepts_anki2_extension():
    """A .anki2 path is accepted without warning."""
    from anki_connect_server.config import Config

    cfg = Config(COLLECTION_PATH="/data/collection.anki2")
    assert cfg.COLLECTION_PATH == "/data/collection.anki2"


def test_config_accepts_extensionless_path():
    """An extensionless path (some users keep their collection without .anki2)
    is accepted so existing setups keep working."""
    from anki_connect_server.config import Config

    cfg = Config(COLLECTION_PATH="/data/anki_db")
    assert cfg.COLLECTION_PATH == "/data/anki_db"
