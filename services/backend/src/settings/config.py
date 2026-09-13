"""Centralized application settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    api_title: str = Field(default="Releasarr API")
    api_version: str = Field(default="0.1.0")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8001)
    api_key: SecretStr = Field(default=SecretStr("dev-secret"))

    database_url: str = Field(default="sqlite+aiosqlite:///./releasarr.db")

    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)
    log_file: str = Field(default=".logs/backend.log")
    # The scheduler is a process of its own and keeps its own file. Sharing one
    # meant that whenever either process rotated it, the other carried on writing
    # to a file that was no longer the active one.
    scheduler_log_file: str = Field(default=".logs/scheduler.log")
    # How many log files the /logs endpoint reaches back through in each of those
    # files, counting the active one. Rotation would otherwise hide a request's
    # history the moment a log grew past its size limit.
    log_history_files: int = Field(default=3, ge=1)

    default_page: int = Field(default=1)
    default_page_size: int = Field(default=20)
    max_page_size: int = Field(default=100)

    sonarr_url: str = Field(default="http://localhost:8989/api/v3")
    sonarr_api_key: SecretStr = Field(default=SecretStr(""))

    radarr_url: str = Field(default="http://localhost:7878/api/v3")
    radarr_api_key: SecretStr = Field(default=SecretStr(""))

    # Sonarr and Radarr refuse an add without a quality profile, which releasarr
    # itself never grabs by. Left unset, the first profile they report is used.
    sonarr_quality_profile_id: int | None = Field(default=None)
    radarr_quality_profile_id: int | None = Field(default=None)

    tvdb_base_url: str = Field(default="https://api4.thetvdb.com/v4")
    tvdb_api_key: SecretStr = Field(default=SecretStr(""))

    tmdb_base_url: str = Field(default="https://api.themoviedb.org/3")
    tmdb_api_key: SecretStr = Field(default=SecretStr(""))

    metadata_languages: tuple[str, ...] = Field(default=("eng", "rus"))

    prowlarr_url: str = Field(default="")
    prowlarr_api_key: SecretStr = Field(default=SecretStr(""))
    prowlarr_categories: tuple[int, ...] = Field(default=())
    prowlarr_timeout: float = Field(default=20.0)

    qbittorrent_url: str = Field(default="")
    qbittorrent_username: str = Field(default="")
    qbittorrent_password: SecretStr = Field(default=SecretStr(""))
    qbittorrent_save_path: str | None = Field(default=None)
    qbittorrent_category: str | None = Field(default=None)
    qbittorrent_tag_prefix: str | None = Field(default=None)
    qbittorrent_paused: bool = Field(default=False)
    qbittorrent_timeout: float = Field(default=15.0)

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
