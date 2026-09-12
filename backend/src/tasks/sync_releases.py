"""Synchronize release stats from qBittorrent to the database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.db.session import DBManager
from src.domain import models
from src.domain.enums import ReleaseStatus
from src.infrastructure.qbittorrent import QbittorrentClient


@dataclass(slots=True)
class SyncResult:
    """Result of a release sync operation."""

    synced: int
    failed: int
    not_found: int


@dataclass(slots=True)
class SyncReleasesTask:
    """Task that synchronizes release stats from qBittorrent.

    This task queries qBittorrent for torrent state and updates
    the corresponding Release records in the database with:
    - progress
    - download_speed / upload_speed
    - seeders / leechers
    - ratio
    - status (based on qBT state)
    - completed_at (when download finishes)
    """

    db: DBManager
    client: QbittorrentClient
    category: str | None = None

    async def execute(self) -> SyncResult:
        """Sync all releases with their qBittorrent state."""
        synced = 0
        failed = 0
        not_found = 0

        # Get all releases from DB
        async with self.db.session() as session:
            stmt = select(models.Release).options(selectinload(models.Release.files))
            result = await session.execute(stmt)
            releases = result.scalars().all()

        # Get all torrents from qBittorrent
        torrents = await self.client.list_torrents(category=self.category)
        torrent_map = {t.get("hash", "").upper(): t for t in torrents}

        # Update each release
        for release in releases:
            info_hash = release.info_hash.upper()
            torrent = torrent_map.get(info_hash)

            if torrent is None:
                not_found += 1
                logger.debug(f"Release {release.id} not found in qBittorrent")
                continue

            try:
                await self._update_release(release.id, torrent)
                synced += 1
            except Exception as exc:
                failed += 1
                logger.error(f"Failed to sync release {release.id}: {exc}")

        return SyncResult(synced=synced, failed=failed, not_found=not_found)

    async def _update_release(self, release_id: str, torrent: dict[str, Any]) -> None:
        """Update a single release with torrent data."""
        async with self.db.transaction() as session:
            release = await session.get(models.Release, release_id)
            if release is None:
                return

            # Map qBT fields to Release model
            release.progress = float(torrent.get("progress", 0)) * 100
            release.download_speed = float(torrent.get("dlspeed", 0))
            release.upload_speed = float(torrent.get("upspeed", 0))
            release.seeders = int(torrent.get("num_seeds", 0))
            release.leechers = int(torrent.get("num_leechs", 0))
            release.ratio = float(torrent.get("ratio", 0))
            release.size_bytes = int(torrent.get("total_size", 0))

            # Map qBT state to ReleaseStatus
            qbt_state = str(torrent.get("state", "")).lower()
            release.status = self._map_status(qbt_state)

            # Set completed_at if download finished
            if release.status == ReleaseStatus.COMPLETED and release.completed_at is None:
                completion_on = torrent.get("completion_on", 0)
                if completion_on and completion_on > 0:
                    release.completed_at = datetime.fromtimestamp(int(completion_on), tz=UTC)

            await session.flush()

    @staticmethod
    def _map_status(qbt_state: str) -> ReleaseStatus:
        """Map qBittorrent state to ReleaseStatus enum."""
        # qBittorrent reports lowercased states here; keep comparisons lowercase.
        if qbt_state in ("downloading", "stalleddl", "queueddl", "forceddl", "metadl"):
            return ReleaseStatus.DOWNLOADING
        if qbt_state in ("uploading", "stalledup", "queuedup", "forcedup"):
            return ReleaseStatus.SEEDING
        if qbt_state in ("pauseddl", "pausedup"):
            return ReleaseStatus.PENDING
        if qbt_state in ("error", "missingfiles"):
            return ReleaseStatus.FAILED
        if qbt_state in ("checkingdl", "checkingup", "checkingresumedata"):
            return ReleaseStatus.DOWNLOADING
        return ReleaseStatus.PENDING


__all__ = ["SyncReleasesTask", "SyncResult"]
