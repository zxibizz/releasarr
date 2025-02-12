from __future__ import annotations

import loguru

from src.application.interfaces.db_manager import I_DBManager
from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.interfaces.torrent_client import I_TorrentClient


class UseCase_ImportReleasesTorrentStats:
    def __init__(
        self,
        db_manager: I_DBManager,
        torrent_client: I_TorrentClient,
        releases_repository: I_ReleasesRepository,
        logger: loguru.Logger,
    ) -> None:
        self.db_manager = db_manager
        self.torrent_client = torrent_client
        self.releases_repository = releases_repository
        self.logger = logger

    async def process(self) -> None:
        self.logger.info("Importing torrent stats")
        with self.logger.catch(reraise=True):
            return await self._process()

    async def _process(self) -> None:
        async with self.db_manager.begin_session() as db_session:
            stats = await self.torrent_client.get_stats()
            torrent_hashes = [t.infohash_v1 for t in stats.torrents.values()]
            releases = await self.releases_repository.get_by_torrent_hashes(
                db_session=db_session, torrent_hashes=torrent_hashes
            )
            for release in releases:
                torrent_stats = stats.torrents[release.qbittorrent_guid]
                release.torrent_is_finished = (
                    torrent_stats.completion_on.timestamp() > 0
                ) and torrent_stats.progress >= 1
                release.torrent_stats_raw = torrent_stats.model_dump_json()
                await self.releases_repository.update(
                    db_session=db_session, release=release
                )
