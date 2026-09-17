"""Tests for the qBittorrent -> database release sync task.

Request-status propagation moved out of this task into
`RequestStateDeriver`/`RecomputeRequestStateUseCase` - see
tests/application/use_cases/requests/test_recompute_request_state.py for that
coverage. This task now only owns the release rows themselves.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from src.db.datetimes import as_utc
from src.db.session import DBManager
from src.domain import models
from src.domain.enums import MediaRequestStatus, MediaType, ReleaseStatus
from src.infrastructure.qbittorrent import QbittorrentClient
from src.tasks.sync_releases import SyncReleasesTask

INFO_HASH = "ABC123"
NOW = datetime(2026, 9, 16, tzinfo=UTC)


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


def finished_torrent(state: str, *, info_hash: str = INFO_HASH) -> dict[str, Any]:
    """A torrent qBittorrent has fully downloaded."""

    return torrent(state, info_hash=info_hash) | {"progress": 1.0, "completion_on": 1_700_000_000}


def make_task(
    db: DBManager,
    torrents: list[dict[str, Any]],
    *,
    grace_seconds: int = 900,
) -> SyncReleasesTask:
    client = cast(QbittorrentClient, FakeQbittorrentClient(torrents))
    return SyncReleasesTask(db=db, client=client, grace_seconds=grace_seconds, clock=lambda: NOW)


async def seed(
    db: DBManager,
    *,
    release_status: ReleaseStatus = ReleaseStatus.PENDING,
    missing_since: datetime | None = None,
    last_exported_info_hash: str | None = None,
) -> None:
    async with db.transaction() as session:
        request = models.MediaRequest(
            id="req-1",
            media_type=MediaType.SERIES,
            status=MediaRequestStatus.DOWNLOADING,
            title="Example - Season 1",
            year=2024,
            genres=[],
            localizations={},
            season_number=1,
            total_episodes=10,
            sonarr_series_id=10,
        )
        session.add(request)
        release = models.Release(
            id="rel-1",
            name="Example.S01.1080p",
            info_hash=INFO_HASH,
            size_bytes=0,
            status=release_status,
            missing_since=missing_since,
            last_exported_info_hash=last_exported_info_hash,
        )
        release.requests.append(request)
        session.add(release)


async def release_record(db: DBManager) -> models.Release:
    async with db.session() as session:
        release = await session.get(models.Release, "rel-1")
        assert release is not None
        return release


@pytest.mark.parametrize("qbt_state", ["uploading", "stalledup", "pausedup"])
async def test_fully_downloaded_torrent_is_completed(
    db_manager: DBManager,
    qbt_state: str,
) -> None:
    """Export depends on this: a seeding state must not mask completion."""

    await seed(db_manager)

    await make_task(db_manager, [finished_torrent(qbt_state)]).execute()

    release = await release_record(db_manager)
    assert release.status == ReleaseStatus.COMPLETED
    assert release.completed_at is not None


async def test_full_progress_without_completion_time_is_not_completed(
    db_manager: DBManager,
) -> None:
    """qBittorrent reports progress 1.0 while still checking a resumed torrent."""

    await seed(db_manager)
    torrent_data = torrent("checkingup") | {"progress": 1.0, "completion_on": 0}

    await make_task(db_manager, [torrent_data]).execute()

    release = await release_record(db_manager)
    assert release.status == ReleaseStatus.DOWNLOADING
    assert release.completed_at is None


async def test_missing_files_outranks_completion(db_manager: DBManager) -> None:
    await seed(db_manager)

    await make_task(db_manager, [finished_torrent("missingfiles")]).execute()

    release = await release_record(db_manager)
    assert release.status == ReleaseStatus.FAILED


async def test_standing_still_is_not_counted_as_synced(db_manager: DBManager) -> None:
    """A seeding torrent reports the same numbers for days; don't rewrite the row."""

    await seed(db_manager)
    task = make_task(db_manager, [finished_torrent("uploading")])

    first = await task.execute()
    second = await task.execute()

    assert (first.synced, first.unchanged) == (1, 0)
    assert (second.synced, second.unchanged) == (0, 1)


async def test_moving_torrent_is_written_again(db_manager: DBManager) -> None:
    await seed(db_manager)
    await make_task(db_manager, [torrent("downloading")]).execute()

    advanced = torrent("downloading") | {"progress": 0.75}
    result = await make_task(db_manager, [advanced]).execute()

    assert (result.synced, result.unchanged) == (1, 0)
    assert (await release_record(db_manager)).progress == 75.0


async def test_a_completed_release_is_not_written_again(db_manager: DBManager) -> None:
    """Seeding stats move every cycle; a finished release is settled at completion."""

    await seed(db_manager)
    task = make_task(db_manager, [finished_torrent("uploading")])
    await task.execute()
    stamped = (await release_record(db_manager)).completed_at

    later = finished_torrent("uploading") | {"completion_on": 1_800_000_000, "upspeed": 99}
    result = await make_task(db_manager, [later]).execute()

    release = await release_record(db_manager)
    assert (result.synced, result.unchanged) == (0, 1)
    assert release.completed_at == stamped
    assert release.upload_speed == 10


async def test_a_completed_release_whose_torrent_returns_clears_the_stamp(
    db_manager: DBManager,
) -> None:
    """The skip must not strand the missing stamp, or the next absence fails it at once."""

    await seed(
        db_manager,
        release_status=ReleaseStatus.COMPLETED,
        missing_since=NOW - timedelta(seconds=60),
    )

    result = await make_task(db_manager, [finished_torrent("uploading")]).execute()

    assert (await release_record(db_manager)).missing_since is None
    assert result.synced == 1


async def test_a_missing_torrent_is_stamped_first_and_left_alone(
    db_manager: DBManager,
) -> None:
    await seed(db_manager, release_status=ReleaseStatus.COMPLETED)

    result = await make_task(
        db_manager, [finished_torrent("uploading", info_hash="OTHER")]
    ).execute()

    release = await release_record(db_manager)
    assert as_utc(release.missing_since) == NOW
    assert release.status == ReleaseStatus.COMPLETED
    assert (result.not_found, result.missing_new) == (1, 1)


async def test_a_missing_torrent_inside_the_grace_period_is_left_alone(
    db_manager: DBManager,
) -> None:
    await seed(
        db_manager,
        release_status=ReleaseStatus.COMPLETED,
        missing_since=NOW - timedelta(seconds=300),
    )

    result = await make_task(
        db_manager, [finished_torrent("uploading", info_hash="OTHER")]
    ).execute()

    release = await release_record(db_manager)
    assert release.status == ReleaseStatus.COMPLETED
    assert result.missing_pending == 1


async def test_a_missing_in_flight_release_is_failed_past_the_grace_period(
    db_manager: DBManager,
) -> None:
    await seed(
        db_manager,
        release_status=ReleaseStatus.COMPLETED,
        missing_since=NOW - timedelta(seconds=901),
    )

    result = await make_task(
        db_manager, [finished_torrent("uploading", info_hash="OTHER")]
    ).execute()

    release = await release_record(db_manager)
    assert release.status == ReleaseStatus.FAILED
    assert result.missing_failed == 1


async def test_a_release_whose_torrent_never_registered_is_failed(
    db_manager: DBManager,
) -> None:
    """A row left on the default pending status is a grab whose add silently failed."""

    await seed(db_manager, missing_since=NOW - timedelta(seconds=901))

    result = await make_task(
        db_manager, [finished_torrent("uploading", info_hash="OTHER")]
    ).execute()

    assert (await release_record(db_manager)).status == ReleaseStatus.FAILED
    assert result.missing_failed == 1


async def test_a_missing_exported_release_is_never_failed(db_manager: DBManager) -> None:
    """A seeded-then-removed torrent is the normal end of a release's life."""

    await seed(
        db_manager,
        release_status=ReleaseStatus.COMPLETED,
        missing_since=NOW - timedelta(days=7),
        last_exported_info_hash=INFO_HASH,
    )

    result = await make_task(
        db_manager, [finished_torrent("uploading", info_hash="OTHER")]
    ).execute()

    release = await release_record(db_manager)
    assert release.status == ReleaseStatus.COMPLETED
    assert (result.missing_failed, result.missing_pending) == (0, 0)


async def test_a_missing_exported_release_is_not_even_stamped(db_manager: DBManager) -> None:
    """Nothing consumes the stamp for a settled release, so it is not tracked at all."""

    await seed(
        db_manager,
        release_status=ReleaseStatus.COMPLETED,
        last_exported_info_hash=INFO_HASH,
    )

    result = await make_task(
        db_manager, [finished_torrent("uploading", info_hash="OTHER")]
    ).execute()

    assert (await release_record(db_manager)).missing_since is None
    assert (result.not_found, result.missing_new) == (1, 0)


async def test_a_reappearing_torrent_clears_the_stamp(db_manager: DBManager) -> None:
    await seed(db_manager, missing_since=NOW - timedelta(seconds=60))
    data = torrent("downloading")

    result = await make_task(db_manager, [data]).execute()

    assert (await release_record(db_manager)).missing_since is None
    assert result.synced == 1


async def test_an_empty_listing_stamps_nothing(db_manager: DBManager) -> None:
    """The sync reads one category, so zero torrents can also mean a re-categorised client."""

    await seed(db_manager, release_status=ReleaseStatus.COMPLETED)

    result = await make_task(db_manager, []).execute()

    release = await release_record(db_manager)
    assert release.missing_since is None
    assert release.status == ReleaseStatus.COMPLETED
    assert (result.not_found, result.missing_new) == (1, 0)


async def test_a_run_with_movement_logs_the_counters(
    db_manager: DBManager,
    captured_records: list[dict[str, Any]],
) -> None:
    """The component filter is the logs view's entry point; a quiet run logs nothing."""

    await seed(db_manager)

    await make_task(db_manager, [torrent("downloading")]).execute()

    summaries = [
        record
        for record in captured_records
        if record["message"] == "Release sync complete"
    ]
    assert len(summaries) == 1
    assert summaries[0]["component"] == "task.release_sync"
    assert summaries[0]["synced"] == 1


async def test_an_unchanged_run_logs_nothing(
    db_manager: DBManager,
    captured_records: list[dict[str, Any]],
) -> None:
    await seed(db_manager)
    task = make_task(db_manager, [finished_torrent("uploading")])
    await task.execute()

    captured_records.clear()
    await task.execute()

    assert [
        record
        for record in captured_records
        if record["message"] == "Release sync complete"
    ] == []


async def test_a_newly_missing_torrent_is_logged(
    db_manager: DBManager,
    captured_records: list[dict[str, Any]],
) -> None:
    await seed(db_manager, release_status=ReleaseStatus.COMPLETED)

    await make_task(db_manager, [finished_torrent("uploading", info_hash="OTHER")]).execute()

    stamped = [
        record
        for record in captured_records
        if record["message"] == "Torrent missing from the download client"
    ]
    assert len(stamped) == 1
    assert stamped[0]["component"] == "task.release_sync"
    assert stamped[0]["release_id"] == "rel-1"
