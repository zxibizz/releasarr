from __future__ import annotations

from datetime import datetime

from loguru import logger
from sqlalchemy import select

from app.clients.factory import get_clients
from app.db.session import AsyncSessionLocal
from app.models import Release
from app.schemas.qbittorrent import Stats


class TorrentStatsImportService:
    def __init__(self) -> None:
        self.clients = get_clients()
        self._session_factory = AsyncSessionLocal

    async def run(self) -> None:
        qb = self.clients.qbittorrent
        if not qb.enabled:
            logger.info("Skipping torrent stats import; qBittorrent disabled")
            return

        stats: Stats = await qb.get_stats()
        if not stats.torrents:
            logger.info("No torrent stats returned by qBittorrent")
            return

        info_hashes = list(stats.torrents.keys())
        async with self._session_factory() as session:
            releases = (
                await session.scalars(
                    select(Release).where(Release.qbittorrent_guid.in_(info_hashes))
                )
            ).all()
            for release in releases:
                torrent_stats = stats.torrents.get(release.qbittorrent_guid)
                if not torrent_stats:
                    continue
                self._apply_stats(release, torrent_stats)
            await session.commit()

    def _apply_stats(self, release: Release, torrent_stats) -> None:
        release.torrent_stats = torrent_stats.model_dump()
        release.download_speed = torrent_stats.dlspeed
        release.upload_speed = torrent_stats.upspeed
        release.seeders = torrent_stats.num_seeds
        release.leechers = torrent_stats.num_leechs
        release.ratio = torrent_stats.ratio
        release.size = torrent_stats.total_size or release.size
        release.progress = round(float(torrent_stats.progress) * 100, 2)
        release.qbittorrent_data = release.qbittorrent_data or {}
        release.qbittorrent_data.update(torrent_stats.model_dump())

        is_complete = torrent_stats.progress >= 1.0
        release.torrent_is_finished = is_complete
        if is_complete:
            release.status = "completed"
            if release.completed_date is None:
                release.completed_date = datetime.utcnow()
        else:
            release.status = "downloading" if torrent_stats.dlspeed > 0 else "pending"
            release.completed_date = None
