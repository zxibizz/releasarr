"""Centralized application settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    api_title: str = Field(default="Releasarr API")
    api_version: str = Field(default="0.1.0")
    api_key: str = Field(default="dev-secret")
    database_url: str = Field(default="sqlite+aiosqlite:///./releasarr.db")

    model_config = {
        "env_prefix": "RELEASARR_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Retrieve cached settings instance."""

    return AppSettings()


__all__ = ["AppSettings", "get_settings"]
