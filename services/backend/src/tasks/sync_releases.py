"""Synchronize release stats from qBittorrent to the database."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.application.utility.torrent_state import project_torrent_state
from src.core.logging import get_logger
from src.db.datetimes import as_utc
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import LogComponent, ReleaseStatus
from src.infrastructure.qbittorrent import QbittorrentClient

_logger = get_logger(LogComponent.TASK_RELEASE_SYNC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class _MissingOutcome(Enum):
    """What one absent torrent implied for its release.

    ``SETTLED`` is deliberately not reported: an exported release losing its
    torrent is routine, and counting it would swamp the outcomes worth watching.
    """

    SETTLED = auto()
    STAMPED = auto()
    PENDING = auto()
    FAILED = auto()


class _UpdateOutcome(Enum):
    """What writing one torrent's state onto its release produced.

    ``COMPLETED`` is the only transition a caller acts on: a download that just
    finished is what the export queue imports, and waiting for the periodic
    sweep to notice it would delay the import by up to that task's interval.
    """

    UNCHANGED = auto()
    MOVED = auto()
    COMPLETED = auto()


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
    # Releases that moved into `completed` during this pass, which the export
    # step reads to decide whether a run is worth queueing.
    completed_now: int = 0


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

    A completed release is not synced at all: seeding stats move on every cycle,
    so it would otherwise be rewritten for as long as it seeds, and nothing
    reads those numbers back once the download is finished.

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
        completed_now = 0
        missing: Counter[_MissingOutcome] = Counter()

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
                missing[await self._reconcile_missing(release, now)] += 1
                continue

            # A stamped-missing completed release still goes through the update:
            # that is the path that clears the stamp when its torrent returns.
            if release.status is ReleaseStatus.COMPLETED and release.missing_since is None:
                unchanged += 1
                continue

            try:
                outcome = await self._update_release(release, torrent)
                if outcome is _UpdateOutcome.UNCHANGED:
                    unchanged += 1
                else:
                    synced += 1
                    if outcome is _UpdateOutcome.COMPLETED:
                        completed_now += 1
            except Exception as exc:
                failed += 1
                _logger.opt(exception=exc).error(
                    f"Failed to sync release {release.id}: {exc}",
                    release_id=release.id,
                    error=str(exc),
                )

        summary = SyncResult(
            synced=synced,
            failed=failed,
            not_found=not_found,
            unchanged=unchanged,
            missing_new=missing[_MissingOutcome.STAMPED],
            missing_pending=missing[_MissingOutcome.PENDING],
            missing_failed=missing[_MissingOutcome.FAILED],
            completed_now=completed_now,
        )
        self._log_run_summary(summary)
        return summary

    def _log_run_summary(self, summary: SyncResult) -> None:
        # Runs every 30s, so the counters only say something when one moved.
        if summary.synced or summary.failed or summary.missing_new or summary.missing_failed:
            _logger.info(
                "Release sync complete",
                synced=summary.synced,
                unchanged=summary.unchanged,
                failed=summary.failed,
                not_found=summary.not_found,
                missing_new=summary.missing_new,
                missing_pending=summary.missing_pending,
                missing_failed=summary.missing_failed,
                completed=summary.completed_now,
            )

    async def _reconcile_missing(self, release: models.Release, now: datetime) -> _MissingOutcome:
        """Track how long a torrent has been gone, failing the release past the grace.

        qBittorrent is the only writer of a release's status, so a removed torrent
        would otherwise leave the row at whatever state it was last seen in —
        including completed, which pins its request on importing forever.
        """

        # An exported release is settled: the arr has the files, the torrent was
        # removed after seeding, and a re-grab adds a fresh one.
        if release.last_exported_info_hash == release.info_hash:
            return _MissingOutcome.SETTLED

        if release.missing_since is None:
            async with self.db.transaction() as session:
                stored = await session.get(models.Release, release.id)
                if stored is not None:
                    stored.missing_since = now
            _logger.info(
                "Torrent missing from the download client",
                release_id=release.id,
                info_hash=release.info_hash,
                status=release.status.value,
            )
            return _MissingOutcome.STAMPED

        age = (now - as_utc(release.missing_since)).total_seconds()
        if age < self.grace_seconds:
            return _MissingOutcome.PENDING

        # A release still pending with no torrent is an add that never landed.
        if release.status is ReleaseStatus.FAILED:
            return _MissingOutcome.PENDING

        async with self.db.transaction() as session:
            stored = await session.get(models.Release, release.id)
            if stored is None:
                return _MissingOutcome.PENDING
            stored.status = ReleaseStatus.FAILED

        for request in release.requests:
            _logger.warning(
                "Torrent missing from the download client past the grace period",
                request_id=request.id,
                release_id=release.id,
                info_hash=release.info_hash,
            )
        return _MissingOutcome.FAILED

    async def _update_release(
        self,
        release: models.Release,
        torrent: dict[str, Any],
    ) -> _UpdateOutcome:
        """Write the torrent's state onto the release, reporting what it did.

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
            return _UpdateOutcome.UNCHANGED

        finishing = (
            release.status is not ReleaseStatus.COMPLETED
            and fields["status"] is ReleaseStatus.COMPLETED
        )

        async with self.db.transaction() as session:
            stored = await session.get(models.Release, release.id)
            if stored is None:
                return _UpdateOutcome.UNCHANGED

            for name, value in fields.items():
                setattr(stored, name, value)

            await session.flush()

        return _UpdateOutcome.COMPLETED if finishing else _UpdateOutcome.MOVED

    def _fields_from_torrent(
        self,
        torrent: dict[str, Any],
        *,
        completed_at: datetime | None,
    ) -> dict[str, Any]:
        """The Release column values a torrent's current state implies."""
        return asdict(project_torrent_state(torrent, completed_at=completed_at))


__all__ = ["SyncReleasesTask", "SyncResult"]
