from __future__ import annotations

from dataclasses import dataclass

from app.clients.prowlarr import ProwlarrClient
from app.clients.qbittorrent import QBittorrentClient
from app.clients.sonarr import SonarrClient
from app.clients.tvdb import TvdbClient
from app.core.config import get_settings


@dataclass(slots=True)
class ExternalClients:
    sonarr: SonarrClient
    tvdb: TvdbClient
    prowlarr: ProwlarrClient
    qbittorrent: QBittorrentClient


_clients: ExternalClients | None = None


def get_clients() -> ExternalClients:
    global _clients
    if _clients is None:
        settings = get_settings()
        _clients = ExternalClients(
            sonarr=SonarrClient(settings),
            tvdb=TvdbClient(settings),
            prowlarr=ProwlarrClient(settings),
            qbittorrent=QBittorrentClient(settings),
        )
    return _clients
