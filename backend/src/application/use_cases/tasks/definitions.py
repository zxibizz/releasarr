"""Catalog of the background tasks Releasarr runs.

Single source of truth for which tasks exist, how often they run on their own,
and which order they must run in when several are triggered together.
"""

from __future__ import annotations

from src.domain.enums import SyncJobKind

DEFAULT_INTERVALS: dict[SyncJobKind, int] = {
    SyncJobKind.SONARR_SYNC: 60 * 60,
    SyncJobKind.RELEASE_SYNC: 30,
    SyncJobKind.EXPORT: 5 * 60,
    SyncJobKind.REGRAB: 60 * 60,
}

# Ordered because later tasks consume what earlier ones produce: the export can
# only import releases the download sync has already marked completed.
TASK_ORDER: tuple[SyncJobKind, ...] = (
    SyncJobKind.SONARR_SYNC,
    SyncJobKind.RELEASE_SYNC,
    SyncJobKind.EXPORT,
    SyncJobKind.REGRAB,
)

SYNC_ALL_SEQUENCE = TASK_ORDER

# A finished download only needs its state refreshed and then imported; the
# Sonarr and indexer tasks are far too slow to run per torrent.
SYNC_DOWNLOADS_SEQUENCE: tuple[SyncJobKind, ...] = (
    SyncJobKind.RELEASE_SYNC,
    SyncJobKind.EXPORT,
)


def interval_for(kind: SyncJobKind) -> int:
    return DEFAULT_INTERVALS[kind]


__all__ = [
    "DEFAULT_INTERVALS",
    "SYNC_ALL_SEQUENCE",
    "SYNC_DOWNLOADS_SEQUENCE",
    "TASK_ORDER",
    "interval_for",
]
