"""Application configuration loaded from environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the bot process."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    discord_token: SecretStr = Field(alias="DISCORD_TOKEN")
    database_url: PostgresDsn = Field(alias="DATABASE_URL")
    dev_guild_ids_value: str = Field(default="", alias="DEV_GUILD_IDS")
    environment: Literal["local", "development", "staging", "production"] = Field(
        default="local",
        alias="ENVIRONMENT",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def dev_guild_ids(self) -> list[int]:
        """Allow comma-separated guild IDs in addition to JSON arrays."""

        raw_value = self.dev_guild_ids_value.strip()
        if not raw_value:
            return []

        if raw_value.startswith("["):
            parsed = json.loads(raw_value)
            if not isinstance(parsed, list):
                raise TypeError("DEV_GUILD_IDS JSON value must be a list")
            return [int(item) for item in parsed]

        return [int(part.strip()) for part in raw_value.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()
