"""Synchronize release stats from qBittorrent to the database."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.application.utility.torrent_state import project_torrent_state
from src.db.datetimes import as_utc
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import ReleaseStatus
from src.infrastructure.qbittorrent import QbittorrentClient


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class SyncResult:
    """Result of a release sync operation."""

    synced: int
    failed: int
    not_found: int
    unchanged: int = 0
    missing_new: int = 0
    missing_pending: int = 0
    missing_failed: int = 0
    requests_updated: int = 0


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

    Releases whose fields already match qBittorrent are left alone, so ``synced``
    counts the releases that actually moved rather than the ones that were looked
    at; ``unchanged`` carries the rest.

    Propagating the refreshed release state onto media requests is
    `SyncSteps.release_sync`'s job, via `RecomputeRequestStateUseCase` - this task
    only owns the release rows themselves.
    """

    db: DBManager
    client: QbittorrentClient
    category: str | None = None
    grace_seconds: int = 900
    clock: Callable[[], datetime] = field(default=_utc_now)

    async def execute(self) -> SyncResult:
        """Sync all releases with their qBittorrent state."""
        synced = 0
        unchanged = 0
        failed = 0
        not_found = 0
        missing_new = 0
        missing_pending = 0
        missing_failed = 0

        # Get all releases from DB
        async with self.db.session() as session:
            stmt = select(models.Release).options(
                selectinload(models.Release.files),
                selectinload(models.Release.requests),
            )
            result = await session.execute(stmt)
            releases = result.scalars().all()

        # Get all torrents from qBittorrent
        torrents = await self.client.list_torrents(category=self.category)
        torrent_map = {t.get("hash", "").upper(): t for t in torrents}
        now = self.clock()

        # Update each release
        for release in releases:
            info_hash = release.info_hash.upper()
            torrent = torrent_map.get(info_hash)

            if torrent is None:
                not_found += 1
                # An empty listing proves nothing: the sync reads only its own
                # category, so a re-categorisation in qBittorrent would look
                # like the whole library vanishing at once.
                if not torrents:
                    continue
                outcome = await self._reconcile_missing(release, now)
                if outcome == "stamped":
                    missing_new += 1
                elif outcome == "failed":
                    missing_failed += 1
                else:
                    missing_pending += 1
                continue

            try:
                if await self._update_release(release, torrent):
                    synced += 1
                else:
                    unchanged += 1
            except Exception as exc:
                failed += 1
                logger.opt(exception=exc).error(
                    f"Failed to sync release {release.id}: {exc}",
                    release_id=release.id,
                    error=str(exc),
                )

        return SyncResult(
            synced=synced,
            failed=failed,
            not_found=not_found,
            unchanged=unchanged,
            missing_new=missing_new,
            missing_pending=missing_pending,
            missing_failed=missing_failed,
        )

    async def _reconcile_missing(self, release: models.Release, now: datetime) -> str:
        """Track how long a torrent has been gone, failing the release past the grace.

        qBittorrent is the only writer of a release's status, so a removed torrent
        would otherwise leave the row at whatever state it was last seen in —
        including completed, which pins its request on importing forever. An
        already-exported release is settled and stays untouched: a
        seeded-then-removed torrent is the normal end of its life.
        """

        if release.missing_since is None:
            async with self.db.transaction() as session:
                stored = await session.get(models.Release, release.id)
                if stored is not None:
                    stored.missing_since = now
            return "stamped"

        age = (now - as_utc(release.missing_since)).total_seconds()
        if age < self.grace_seconds:
            return "pending"

        in_flight = release.last_exported_info_hash != release.info_hash
        if not in_flight or release.status not in (
            ReleaseStatus.DOWNLOADING,
            ReleaseStatus.COMPLETED,
        ):
            return "pending"

        async with self.db.transaction() as session:
            stored = await session.get(models.Release, release.id)
            if stored is None:
                return "pending"
            stored.status = ReleaseStatus.FAILED

        for request in release.requests:
            logger.warning(
                "Torrent missing from the download client past the grace period",
                request_id=request.id,
                release_id=release.id,
                info_hash=release.info_hash,
            )
        return "failed"

    async def _update_release(self, release: models.Release, torrent: dict[str, Any]) -> bool:
        """Write the torrent's state onto the release, reporting whether it moved.

        A release lives in the database for as long as it seeds, which is usually
        far longer than it downloads, so on a typical cycle every field already
        holds the value qBittorrent reports. Comparing before opening a
        transaction keeps those cycles from rewriting - and re-fsyncing - rows
        that nothing has changed.
        """
        fields = self._fields_from_torrent(torrent, completed_at=release.completed_at)
        # A torrent that is back clears the stamp; one that was never missing
        # already holds None, so the compare-before-write fast path still skips it.
        fields["missing_since"] = None
        if all(getattr(release, name) == value for name, value in fields.items()):
            return False

        async with self.db.transaction() as session:
            stored = await session.get(models.Release, release.id)
            if stored is None:
                return False

            for name, value in fields.items():
                setattr(stored, name, value)

            await session.flush()

        return True

    def _fields_from_torrent(
        self,
        torrent: dict[str, Any],
        *,
        completed_at: datetime | None,
    ) -> dict[str, Any]:
        """The Release column values a torrent's current state implies."""
        return asdict(project_torrent_state(torrent, completed_at=completed_at))


__all__ = ["SyncReleasesTask", "SyncResult"]
