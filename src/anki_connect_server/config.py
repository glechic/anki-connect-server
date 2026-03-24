from typing import Optional
from pydantic import field_validator, model_validator
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

    ANKIWEB_USER: Optional[str] = None
    ANKIWEB_PASS: Optional[str] = None

    ANKIWEB_URL: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_collection_path(cls, values):
        if not values.get("COLLECTION_PATH"):
            raise ValueError("ANKICONNECT_COLLECTION_PATH environment variable is required")
        return values


config = Config()