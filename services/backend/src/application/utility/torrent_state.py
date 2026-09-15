"""Projection of a download client's torrent record onto release-level state.

Shared by the scheduled sync task and the on-demand release refresh, so both
read a torrent the same way: a finished torrent keeps seeding, which makes its
reported state useless for deciding whether the download is done.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from src.application.interfaces.releases import ReleaseTorrentState
from src.domain.enums import ReleaseStatus


def project_torrent_state(
    torrent: Mapping[str, Any],
    *,
    completed_at: datetime | None = None,
) -> ReleaseTorrentState:
    """The release state a torrent's reported fields imply.

    ``completed_at`` is the value already stored for the release, when the caller
    has one: it is stamped once and never revised, so a later read fills it in
    only if it is still missing.
    """

    qbt_state = str(torrent.get("state", "")).lower()
    status = _map_status(qbt_state, finished=_is_finished(torrent))

    return ReleaseTorrentState(
        progress=float(torrent.get("progress", 0)) * 100,
        download_speed=float(torrent.get("dlspeed", 0)),
        upload_speed=float(torrent.get("upspeed", 0)),
        seeders=int(torrent.get("num_seeds", 0)),
        leechers=int(torrent.get("num_leechs", 0)),
        ratio=float(torrent.get("ratio", 0)),
        size_bytes=int(torrent.get("total_size", 0)),
        status=status,
        completed_at=_completion_time(torrent, status, completed_at),
    )


def _completion_time(
    torrent: Mapping[str, Any],
    status: ReleaseStatus,
    current: datetime | None,
) -> datetime | None:
    if current is not None or status is not ReleaseStatus.COMPLETED:
        return current

    completion_on = int(torrent.get("completion_on", 0) or 0)
    if completion_on <= 0:
        return None

    return datetime.fromtimestamp(completion_on, tz=UTC)


def _is_finished(torrent: Mapping[str, Any]) -> bool:
    progress = float(torrent.get("progress", 0) or 0)
    completion_on = int(torrent.get("completion_on", 0) or 0)
    return progress >= 1.0 and completion_on > 0


def _map_status(qbt_state: str, *, finished: bool = False) -> ReleaseStatus:
    """Map a qBittorrent state onto a release status.

    qBittorrent reports lowercased states here; comparisons stay lowercase.
    Errors outrank completion: a torrent whose files vanished after finishing
    has nothing left to import.
    """

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


__all__ = ["project_torrent_state"]
