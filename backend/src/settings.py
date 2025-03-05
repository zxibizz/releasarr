from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=False,
        extra="ignore",
    )

    DB_PATH: str

    TVDB_API_TOKEN: str

    PROWLARR_BASE_URL: str
    PROWLARR_API_TOKEN: str

    SONARR_API_TOKEN: str
    SONARR_BASE_URL: str

    QBITTORRENT_BASE_URL: str
    QBITTORRENT_USERNAME: str
    QBITTORRENT_PASSWORD: str

    LOG_FILE: str = "logs/log.log"


app_settings = AppSettings()
