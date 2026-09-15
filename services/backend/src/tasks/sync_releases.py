"""Synchronize release stats from qBittorrent to the database."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.application.interfaces.releases import MANUAL_SOURCE
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, ReleaseStatus
from src.infrastructure.qbittorrent import QbittorrentClient

# Release states that mean a grab is in flight for the owning request. Seeding and
# completed torrents count: the bytes are on disk but Sonarr has not imported them
# yet, so the request is still being worked on.
ACTIVE_RELEASE_STATUSES = frozenset(
    {ReleaseStatus.DOWNLOADING, ReleaseStatus.SEEDING, ReleaseStatus.COMPLETED}
)


def _is_in_flight(release: models.Release) -> bool:
    """Whether the release still has anything to do for its requests.

    A release the export has already imported is done with: the torrent is only
    still around because it seeds. Counting it as in flight would hold the request
    on ``downloading`` for as long as qBittorrent keeps the torrent, and a request
    held there is never searched again.
    """

    return release.last_exported_info_hash != release.info_hash


def _is_regrabbable(release: models.Release) -> bool:
    """Whether the re-grab pass could still find a better copy of this release.

    ``torrent_source`` names the indexer Prowlarr attributed the release to, so a
    release carrying one can be searched for again. A hand-supplied torrent has no
    indexer to go back to and nothing will ever replace it.
    """

    return release.torrent_source is not None and release.torrent_source != MANUAL_SOURCE


@dataclass(slots=True)
class SyncResult:
    """Result of a release sync operation."""

    synced: int
    failed: int
    not_found: int
    unchanged: int = 0
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

    It then propagates the refreshed release statuses onto the media requests those
    releases belong to, so a request reflects that a download is under way.
    """

    db: DBManager
    client: QbittorrentClient
    category: str | None = None

    async def execute(self) -> SyncResult:
        """Sync all releases with their qBittorrent state."""
        synced = 0
        unchanged = 0
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

        requests_updated = await self._sync_request_statuses()

        return SyncResult(
            synced=synced,
            failed=failed,
            not_found=not_found,
            unchanged=unchanged,
            requests_updated=requests_updated,
        )

    async def _update_release(self, release: models.Release, torrent: dict[str, Any]) -> bool:
        """Write the torrent's state onto the release, reporting whether it moved.

        A release lives in the database for as long as it seeds, which is usually
        far longer than it downloads, so on a typical cycle every field already
        holds the value qBittorrent reports. Comparing before opening a
        transaction keeps those cycles from rewriting - and re-fsyncing - rows
        that nothing has changed.
        """
        fields = self._fields_from_torrent(torrent, completed_at=release.completed_at)
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
        qbt_state = str(torrent.get("state", "")).lower()
        status = self._map_status(qbt_state, finished=self._is_finished(torrent))

        return {
            "progress": float(torrent.get("progress", 0)) * 100,
            "download_speed": float(torrent.get("dlspeed", 0)),
            "upload_speed": float(torrent.get("upspeed", 0)),
            "seeders": int(torrent.get("num_seeds", 0)),
            "leechers": int(torrent.get("num_leechs", 0)),
            "ratio": float(torrent.get("ratio", 0)),
            "size_bytes": int(torrent.get("total_size", 0)),
            "status": status,
            "completed_at": self._completion_time(torrent, status, completed_at),
        }

    @staticmethod
    def _completion_time(
        torrent: dict[str, Any],
        status: ReleaseStatus,
        current: datetime | None,
    ) -> datetime | None:
        """When the download finished, stamped once and never revised afterwards."""
        if current is not None or status is not ReleaseStatus.COMPLETED:
            return current

        completion_on = int(torrent.get("completion_on", 0) or 0)
        if completion_on <= 0:
            return None

        return datetime.fromtimestamp(completion_on, tz=UTC)

    async def _sync_request_statuses(self) -> int:
        """Reflect the state of each request's releases on the request itself.

        Completed requests are skipped: Sonarr owns that transition (a season is only
        done once it stops being reported missing), and a finished torrent usually
        keeps seeding long after the import, which would otherwise flip the request
        back and forth on every cycle.
        """
        updated = 0
        async with self.db.transaction() as session:
            stmt = (
                select(models.MediaRequest)
                .where(models.MediaRequest.status != MediaRequestStatus.COMPLETED)
                .where(models.MediaRequest.releases.any())
                .options(selectinload(models.MediaRequest.releases))
            )
            result = await session.execute(stmt)

            for request in result.scalars():
                derived = self._derive_request_status(request.releases)
                if derived is None or derived == request.status:
                    continue
                previous = request.status
                request.status = derived
                updated += 1
                logger.info(
                    f"Request status changed from {previous.value} to {derived.value}",
                    request_id=request.id,
                    previous_status=previous.value,
                    status=derived.value,
                )

            await session.flush()

        return updated

    @staticmethod
    def _derive_request_status(
        releases: Sequence[models.Release],
    ) -> MediaRequestStatus | None:
        """Status implied by a request's releases, or None to leave it untouched.

        With nothing in flight the request's grabs have all been imported. That is
        not necessarily the end of it: an indexer-sourced release can be searched
        for again, so the request is monitoring rather than waiting on anything.
        Releases that came in by hand leave the status as the request sync set it,
        because nothing will ever re-grab them.
        """

        in_flight = [release for release in releases if _is_in_flight(release)]
        if in_flight:
            if any(release.status in ACTIVE_RELEASE_STATUSES for release in in_flight):
                return MediaRequestStatus.DOWNLOADING
            if all(release.status == ReleaseStatus.FAILED for release in in_flight):
                return MediaRequestStatus.FAILED
            return None
        if any(_is_regrabbable(release) for release in releases):
            return MediaRequestStatus.MONITORING
        return None

    @staticmethod
    def _is_finished(torrent: dict[str, Any]) -> bool:
        """Whether qBittorrent has the complete payload on disk.

        Derived from progress and completion time rather than the reported state,
        because a finished torrent keeps seeding and therefore reports an upload
        state indistinguishable from one that never finished downloading.
        """
        progress = float(torrent.get("progress", 0) or 0)
        completion_on = int(torrent.get("completion_on", 0) or 0)
        return progress >= 1.0 and completion_on > 0

    @staticmethod
    def _map_status(qbt_state: str, *, finished: bool = False) -> ReleaseStatus:
        """Map qBittorrent state to ReleaseStatus enum."""
        # qBittorrent reports lowercased states here; keep comparisons lowercase.
        # Errors outrank completion: a torrent whose files vanished after finishing
        # has nothing left to import.
        if qbt_state in ("error", "missingfiles"):
            return ReleaseStatus.FAILED
        if finished:
            return ReleaseStatus.COMPLETED
        if qbt_state in ("downloading", "stalleddl", "queueddl", "forceddl", "metadl"):
            return ReleaseStatus.DOWNLOADING
        if qbt_state in ("uploading", "stalledup", "queuedup", "forcedup"):
            return ReleaseStatus.SEEDING
        if qbt_state in ("pauseddl", "pausedup"):
            return ReleaseStatus.PENDING
        if qbt_state in ("checkingdl", "checkingup", "checkingresumedata"):
            return ReleaseStatus.DOWNLOADING
        return ReleaseStatus.PENDING


__all__ = ["SyncReleasesTask", "SyncResult"]
