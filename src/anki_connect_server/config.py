import tempfile
from functools import cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_collection_path() -> str:
    """Return a temp path for a fresh Anki collection.

    Used when ``ANKICONNECT_COLLECTION_PATH`` is not configured, so the server
    can boot without an existing collection (e.g. for testing or first run).
    """
    return str(Path(tempfile.gettempdir()) / "anki-connect-server" / "collection.anki2")


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="ANKICONNECT_",
    )

    PORT: int = 8765
    BIND: str = "127.0.0.1"

    COLLECTION_PATH: str = ""

    ANKIWEB_USER: str | None = None
    ANKIWEB_PASS: str | None = None

    ANKIWEB_URL: str | None = None

    @field_validator("COLLECTION_PATH")
    @classmethod
    def _validate_collection_path(cls, v: str) -> str:
        if not v:
            return _default_collection_path()
        return v


@cache
def get_config() -> Config:
    return Config()
