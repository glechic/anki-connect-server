from functools import cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        return v


@cache
def get_config() -> Config:
    return Config()
