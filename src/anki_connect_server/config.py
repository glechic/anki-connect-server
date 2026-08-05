import logging
from functools import cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
            raise ValueError(
                "ANKICONNECT_COLLECTION_PATH must be set to an Anki collection file "
                "(typically a .anki2 file)"
            )
        if v.endswith(".anki21"):
            logger.warning(
                "ANKICONNECT_COLLECTION_PATH %r uses the deprecated '.anki21' "
                "extension; Anki has consolidated on '.anki2'. Consider renaming.",
                v,
            )
        return v


@cache
def get_config() -> Config:
    return Config()


config = Config()
