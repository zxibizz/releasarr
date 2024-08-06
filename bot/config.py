from dataclasses import dataclass

_dependencies: "Dependencies"


@dataclass
class Dependencies:
    tvdb_api_client: None
    sonarr_api_client: None
    prowlarr_api_client: None
    sync_manager: None
    qbittorrent_api_client: None


def init_dependencies(overrides: dict | None = None):
    from bot.dependencies.prowlarr import ProwlarrApiClient
    from bot.dependencies.qbittorrent import QBittorrentApiClient
    from bot.dependencies.sonarr import SonarrApiClient
    from bot.dependencies.tvdb import TVDBApiClient
    from bot.utils.sync_manager import SyncManager

    global _dependencies
    overrides = overrides or {}

    _dependencies = Dependencies(
        tvdb_api_client=overrides.get(
            "tvdb_api_client",
            TVDBApiClient(),
        ),
        sonarr_api_client=overrides.get(
            "sonarr_api_client",
            SonarrApiClient(),
        ),
        prowlarr_api_client=overrides.get(
            "prowlarr_api_client",
            ProwlarrApiClient(),
        ),
        sync_manager=overrides.get(
            "sync_manager",
            SyncManager(),
        ),
        qbittorrent_api_client=overrides.get(
            "qbittorrent_api_client",
            QBittorrentApiClient(),
        ),
    )


def get_dependecies():
    global _dependencies
    return _dependencies
