"""Unit tests for `RequestStateDeriver` and `RecomputeRequestStateUseCase`."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.application.interfaces.media_requests import MediaRequestRecord, UpdateMediaRequestData
from src.application.interfaces.releases import ReleaseRecord
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import ArrCompletion, RequestStateDeriver
from src.application.utility.sentinels import UNSET
from src.domain.enums import MediaRequestStatus, ReleaseStatus
from tests.fakes import FakeMediaRequestRepository, make_record

REQUEST_ID = "req-1"


def make_release(
    release_id: str,
    *,
    request_ids: list[str],
    status: ReleaseStatus = ReleaseStatus.DOWNLOADING,
    info_hash: str = "hash",
    last_exported_info_hash: str | None = None,
    torrent_source: str | None = "indexer",
    published_at: datetime | None = None,
) -> ReleaseRecord:
    return ReleaseRecord(
        id=release_id,
        name=release_id,
        info_hash=info_hash,
        size_bytes=1024,
        status=status,
        progress=0.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=0,
        leechers=0,
        ratio=0.0,
        added_at=datetime.now(UTC),
        completed_at=None,
        request_ids=request_ids,
        requests=[],
        torrent_source=torrent_source,
        quality="1080p",
        files=[],
        last_exported_info_hash=last_exported_info_hash,
        export_failures_count=0,
        published_at=published_at,
    )


class FakeReleaseRepository:
    """Serves whichever release set the test wants for `get_releases_for_requests`."""

    def __init__(self, releases: list[ReleaseRecord]) -> None:
        self._releases = releases

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        wanted = set(request_ids)
        return [release for release in self._releases if wanted & set(release.request_ids)]


class FakeWarningSynchronizer:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def sync_for_requests(self, request_ids: list[str]) -> None:
        self.calls.append(sorted(request_ids))


# --- RequestStateDeriver ----------------------------------------------------


def test_arr_complete_wins_regardless_of_releases() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    release = make_release(
        "rel-1", request_ids=[REQUEST_ID], status=ReleaseStatus.FAILED, last_exported_info_hash=None
    )

    derived = RequestStateDeriver().derive(record, [release], ArrCompletion(is_complete=True))

    assert derived.status is MediaRequestStatus.COMPLETED


def test_arr_says_not_complete_reopens_a_completed_request() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.COMPLETED)

    derived = RequestStateDeriver().derive(record, [], ArrCompletion(is_complete=False))

    assert derived.status is MediaRequestStatus.PENDING


def test_completed_request_is_untouched_without_an_arr_verdict() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.COMPLETED)
    release = make_release("rel-1", request_ids=[REQUEST_ID], status=ReleaseStatus.SEEDING)

    derived = RequestStateDeriver().derive(record, [release], arr=None)

    assert derived.status is UNSET


def test_active_in_flight_release_moves_to_downloading() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    release = make_release(
        "rel-1",
        request_ids=[REQUEST_ID],
        status=ReleaseStatus.SEEDING,
        info_hash="hash",
        last_exported_info_hash=None,
    )

    derived = RequestStateDeriver().derive(record, [release], arr=None)

    assert derived.status is MediaRequestStatus.DOWNLOADING


def test_all_failed_in_flight_releases_move_to_failed() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    release = make_release(
        "rel-1",
        request_ids=[REQUEST_ID],
        status=ReleaseStatus.FAILED,
        info_hash="hash",
        last_exported_info_hash=None,
    )

    derived = RequestStateDeriver().derive(record, [release], arr=None)

    assert derived.status is MediaRequestStatus.FAILED


def test_mixed_in_flight_releases_leave_status_untouched() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    releases = [
        make_release(
            "rel-1",
            request_ids=[REQUEST_ID],
            status=ReleaseStatus.PENDING,
            info_hash="a",
            last_exported_info_hash=None,
        ),
        make_release(
            "rel-2",
            request_ids=[REQUEST_ID],
            status=ReleaseStatus.FAILED,
            info_hash="b",
            last_exported_info_hash=None,
        ),
    ]

    derived = RequestStateDeriver().derive(record, releases, arr=None)

    assert derived.status is UNSET


def test_regrabbable_release_with_nothing_in_flight_moves_to_monitoring() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    release = make_release(
        "rel-1",
        request_ids=[REQUEST_ID],
        status=ReleaseStatus.COMPLETED,
        info_hash="hash",
        last_exported_info_hash="hash",
        torrent_source="indexer",
    )

    derived = RequestStateDeriver().derive(record, [release], arr=None)

    assert derived.status is MediaRequestStatus.MONITORING


def test_manual_release_with_nothing_in_flight_settles_on_pending() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    release = make_release(
        "rel-1",
        request_ids=[REQUEST_ID],
        status=ReleaseStatus.COMPLETED,
        info_hash="hash",
        last_exported_info_hash="hash",
        torrent_source="manual",
    )

    derived = RequestStateDeriver().derive(record, [release], arr=None)

    assert derived.status is MediaRequestStatus.PENDING


def test_no_releases_settles_on_pending() -> None:
    """Heals a request whose last release was deleted rather than leaving it stale."""
    record = make_record(REQUEST_ID, status=MediaRequestStatus.DOWNLOADING)

    derived = RequestStateDeriver().derive(record, [], arr=None)

    assert derived.status is MediaRequestStatus.PENDING


def test_newest_published_at_is_the_max_across_releases_ignoring_none() -> None:
    record = make_record(REQUEST_ID)
    releases = [
        make_release(
            "rel-1", request_ids=[REQUEST_ID], published_at=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        make_release(
            "rel-2", request_ids=[REQUEST_ID], published_at=datetime(2026, 3, 1, tzinfo=UTC)
        ),
        make_release("rel-3", request_ids=[REQUEST_ID], published_at=None),
    ]

    derived = RequestStateDeriver().derive(record, releases, arr=None)

    assert derived.newest_release_published_at == datetime(2026, 3, 1, tzinfo=UTC)


# --- RecomputeRequestStateUseCase -------------------------------------------


@pytest.mark.asyncio
async def test_recompute_is_a_no_op_for_empty_input() -> None:
    repository = FakeMediaRequestRepository()
    warning_synchronizer = FakeWarningSynchronizer()
    use_case = RecomputeRequestStateUseCase(
        repository=repository,
        release_repository=FakeReleaseRepository([]),
        warning_synchronizer=warning_synchronizer,  # type: ignore[arg-type]
    )

    result = await use_case.execute([])

    assert result.updated == 0
    assert warning_synchronizer.calls == []


@pytest.mark.asyncio
async def test_recompute_skips_missing_requests() -> None:
    repository = FakeMediaRequestRepository()
    warning_synchronizer = FakeWarningSynchronizer()
    use_case = RecomputeRequestStateUseCase(
        repository=repository,
        release_repository=FakeReleaseRepository([]),
        warning_synchronizer=warning_synchronizer,  # type: ignore[arg-type]
    )

    result = await use_case.execute(["missing"])

    assert result.updated == 0
    assert warning_synchronizer.calls == [["missing"]]


@pytest.mark.asyncio
async def test_recompute_writes_a_changed_status_and_syncs_warnings() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    repository = FakeMediaRequestRepository({REQUEST_ID: record})
    release = make_release(
        "rel-1",
        request_ids=[REQUEST_ID],
        status=ReleaseStatus.SEEDING,
        info_hash="hash",
        last_exported_info_hash=None,
    )
    warning_synchronizer = FakeWarningSynchronizer()
    use_case = RecomputeRequestStateUseCase(
        repository=repository,
        release_repository=FakeReleaseRepository([release]),
        warning_synchronizer=warning_synchronizer,  # type: ignore[arg-type]
    )

    result = await use_case.execute([REQUEST_ID])

    assert result.updated == 1
    assert repository.records[REQUEST_ID].status is MediaRequestStatus.DOWNLOADING
    assert warning_synchronizer.calls == [[REQUEST_ID]]


@pytest.mark.asyncio
async def test_recompute_is_a_no_op_when_nothing_changed() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)

    class RecordingRepository(FakeMediaRequestRepository):
        def __init__(self, records: dict[str, MediaRequestRecord]) -> None:
            super().__init__(records)
            self.update_calls = 0

        async def update_request(
            self, request_id: str, data: UpdateMediaRequestData
        ) -> MediaRequestRecord | None:
            self.update_calls += 1
            return await super().update_request(request_id, data)

    recording_repository = RecordingRepository({REQUEST_ID: record})
    warning_synchronizer = FakeWarningSynchronizer()
    use_case = RecomputeRequestStateUseCase(
        repository=recording_repository,
        release_repository=FakeReleaseRepository([]),
        warning_synchronizer=warning_synchronizer,  # type: ignore[arg-type]
    )

    result = await use_case.execute([REQUEST_ID])

    assert result.updated == 0
    assert recording_repository.update_calls == 0
    assert warning_synchronizer.calls == [[REQUEST_ID]]


@pytest.mark.asyncio
async def test_recompute_applies_the_arr_verdict_for_the_matching_request() -> None:
    record = make_record(REQUEST_ID, status=MediaRequestStatus.PENDING)
    repository = FakeMediaRequestRepository({REQUEST_ID: record})
    warning_synchronizer = FakeWarningSynchronizer()
    use_case = RecomputeRequestStateUseCase(
        repository=repository,
        release_repository=FakeReleaseRepository([]),
        warning_synchronizer=warning_synchronizer,  # type: ignore[arg-type]
    )

    result = await use_case.execute(
        [REQUEST_ID], arr_completion={REQUEST_ID: ArrCompletion(is_complete=True)}
    )

    assert result.updated == 1
    assert repository.records[REQUEST_ID].status is MediaRequestStatus.COMPLETED
