import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=False,
        extra="ignore",
    )

    DB_CONNECTION_STRING: str = os.getenv(
        "DB_CONNECTION_STRING",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/releasarr",
    )

    TVDB_API_TOKEN: str = os.getenv("TVDB_API_TOKEN", "")

    PROWLARR_BASE_URL: str = os.getenv("PROWLARR_BASE_URL", "http://localhost:9696")
    PROWLARR_API_TOKEN: str = os.getenv("PROWLARR_API_TOKEN", "")

    SONARR_API_TOKEN: str = os.getenv("SONARR_API_TOKEN", "")
    SONARR_BASE_URL: str = os.getenv("SONARR_BASE_URL", "http://localhost:8989")

    QBITTORRENT_BASE_URL: str = os.getenv(
        "QBITTORRENT_BASE_URL", "http://localhost:8080"
    )
    QBITTORRENT_USERNAME: str = os.getenv("QBITTORRENT_USERNAME", "admin")
    QBITTORRENT_PASSWORD: str = os.getenv("QBITTORRENT_PASSWORD", "adminadmin")

    LOG_FILE: str = os.getenv("LOG_FILE", "logs/log.log")
    ENABLE_TASK_SCHEDULER: bool = (
        os.getenv("ENABLE_TASK_SCHEDULER", "False").lower() == "true"
    )


app_settings = AppSettings()
