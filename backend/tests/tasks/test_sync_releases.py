"""Tests for the qBittorrent -> database release sync task."""

from __future__ import annotations

from typing import Any, cast

import pytest

from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus
from src.infrastructure.qbittorrent import QbittorrentClient
from src.tasks.sync_releases import SyncReleasesTask

INFO_HASH = "ABC123"


class FakeQbittorrentClient:
    def __init__(self, torrents: list[dict[str, Any]]) -> None:
        self._torrents = torrents

    async def list_torrents(
        self,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._torrents


def torrent(state: str, *, info_hash: str = INFO_HASH) -> dict[str, Any]:
    return {
        "hash": info_hash,
        "state": state,
        "progress": 0.5,
        "dlspeed": 1000,
        "upspeed": 10,
        "num_seeds": 3,
        "num_leechs": 1,
        "ratio": 0.2,
        "total_size": 2048,
    }


def make_task(db: DBManager, torrents: list[dict[str, Any]]) -> SyncReleasesTask:
    client = cast(QbittorrentClient, FakeQbittorrentClient(torrents))
    return SyncReleasesTask(db=db, client=client)


async def seed(
    db: DBManager,
    *,
    request_status: MediaRequestStatus,
    release_status: ReleaseStatus = ReleaseStatus.PENDING,
    with_release: bool = True,
) -> None:
    async with db.transaction() as session:
        request = models.MediaRequest(
            id="req-1",
            media_type=MediaType.SERIES,
            status=request_status,
            title="Example - Season 1",
            year=2024,
            genres=[],
            localizations={},
            season_number=1,
            total_episodes=10,
            sonarr_series_id=10,
        )
        session.add(request)
        if with_release:
            release = models.Release(
                id="rel-1",
                name="Example.S01.1080p",
                info_hash=INFO_HASH,
                size_bytes=0,
                status=release_status,
            )
            release.requests.append(request)
            session.add(release)


async def request_status(db: DBManager) -> MediaRequestStatus:
    async with db.session() as session:
        request = await session.get(models.MediaRequest, "req-1")
        assert request is not None
        return request.status


@pytest.mark.parametrize(
    ("qbt_state", "expected"),
    [
        ("downloading", MediaRequestStatus.DOWNLOADING),
        ("metadl", MediaRequestStatus.DOWNLOADING),
        # A finished torrent keeps seeding while Sonarr has yet to import it, so the
        # request is still in flight rather than done.
        ("uploading", MediaRequestStatus.DOWNLOADING),
        ("error", MediaRequestStatus.FAILED),
    ],
)
async def test_release_state_drives_request_status(
    db_manager: DBManager,
    qbt_state: str,
    expected: MediaRequestStatus,
) -> None:
    await seed(db_manager, request_status=MediaRequestStatus.PENDING)

    result = await make_task(db_manager, [torrent(qbt_state)]).execute()

    assert result.requests_updated == 1
    assert await request_status(db_manager) == expected


async def test_completed_request_is_not_downgraded(db_manager: DBManager) -> None:
    """Sonarr owns completion; a still-seeding torrent must not undo it."""

    await seed(db_manager, request_status=MediaRequestStatus.COMPLETED)

    result = await make_task(db_manager, [torrent("uploading")]).execute()

    assert result.requests_updated == 0
    assert await request_status(db_manager) == MediaRequestStatus.COMPLETED


async def test_paused_torrent_does_not_downgrade_request(db_manager: DBManager) -> None:
    await seed(db_manager, request_status=MediaRequestStatus.DOWNLOADING)

    result = await make_task(db_manager, [torrent("pauseddl")]).execute()

    assert result.requests_updated == 0
    assert await request_status(db_manager) == MediaRequestStatus.DOWNLOADING


async def test_request_without_releases_is_untouched(db_manager: DBManager) -> None:
    await seed(db_manager, request_status=MediaRequestStatus.PENDING, with_release=False)

    result = await make_task(db_manager, []).execute()

    assert result.requests_updated == 0
    assert await request_status(db_manager) == MediaRequestStatus.PENDING
