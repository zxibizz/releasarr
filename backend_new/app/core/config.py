from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="allow", case_sensitive=False
    )

    app_name: str = Field(default="Releasarr Backend")
    environment: Literal["development", "production", "test"] = Field(
        default="development"
    )

    database_url: str = Field(
        default="sqlite+aiosqlite:///./db.sqlite3",
        description="SQLAlchemy database URL",
    )

    # External services
    sonarr_url: AnyHttpUrl | None = Field(default=None)
    sonarr_api_key: str | None = Field(default=None)

    tvdb_url: AnyHttpUrl | None = Field(default=None)
    tvdb_api_key: str | None = Field(default=None)

    prowlarr_url: AnyHttpUrl | None = Field(default=None)
    prowlarr_api_key: str | None = Field(default=None)

    qbittorrent_url: AnyHttpUrl | None = Field(default=None)
    qbittorrent_username: str | None = Field(default=None)
    qbittorrent_password: str | None = Field(default=None)

    mock_external_services: bool = Field(
        default=True,
        description="If true, HTTP integrations will be replaced with mock implementations.",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
