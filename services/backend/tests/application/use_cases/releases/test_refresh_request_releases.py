"""Tests for refreshing a request's releases on demand.

The two halves are covered from opposite ends: a release still in flight is only
ever out of date relative to the download client, and a finished one only ever
out of date because its indexer replaced the torrent.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.interfaces.indexers import IndexerRecord
from src.application.interfaces.media_requests import MediaRequestRecord
from src.application.interfaces.releases import (
    QueuedDownload,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchUnavailableError,
    ReleaseTorrentState,
)
from src.application.use_cases.auth.permissions import RequestScope
from src.application.use_cases.indexers.exceptions import ProwlarrNotConfiguredError
from src.application.use_cases.releases.commands import RefreshRequestReleasesCommand
from src.application.use_cases.releases.dto import ReleaseRefreshDTO
from src.application.use_cases.releases.exceptions import QbittorrentNotConfiguredError
from src.application.use_cases.releases.refresh_request_releases import (
    RefreshRequestReleasesUseCase,
)
from src.application.use_cases.releases.regrab import ReleaseRegrapper
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.domain.enums import ReleaseStatus
from tests.builders import stub_recompute_state, stub_warning_repository
from tests.fakes import (
    UnusedIndexerDirectoryCalls,
    UnusedMediaRequestCalls,
    UnusedReleaseDownloadCalls,
    UnusedReleaseRepositoryCalls,
    make_record,
)

REQUEST_ID = "req-1"
RELEASE_ID = "rel-1"
OWNER_ID = "owner-1"


def make_release(
    *,
    release_id: str = RELEASE_ID,
    status: ReleaseStatus = ReleaseStatus.DOWNLOADING,
    info_hash: str = "OLDHASH",
    torrent_source: str | None = "RuTracker",
    progress: float = 10.0,
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id=release_id,
        name="Old.Release.Name",
        info_hash=info_hash,
        size_bytes=1024,
        status=status,
        progress=progress,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=1,
        leechers=0,
        ratio=1.0,
        added_at=now,
        completed_at=now,
        request_ids=[REQUEST_ID],
        requests=[],
        torrent_source=torrent_source,
        quality="1080p",
        files=[],
        last_exported_info_hash=None,
        export_failures_count=0,
        info_url="https://tracker.example/details/1",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def state_for(release: ReleaseRecord, **overrides: Any) -> ReleaseTorrentState:
    """What the client reports for a release that has not moved."""

    fields: dict[str, Any] = {
        "progress": release.progress,
        "download_speed": release.download_speed,
        "upload_speed": release.upload_speed,
        "seeders": release.seeders,
        "leechers": release.leechers,
        "ratio": release.ratio,
        "size_bytes": release.size_bytes,
        "status": release.status,
        "completed_at": release.completed_at,
    }
    fields.update(overrides)
    return ReleaseTorrentState(**fields)


def make_match(magnet_link: str = "magnet:?xt=urn:btih:NEWHASH") -> ReleaseSearchResultRecord:
    return ReleaseSearchResultRecord(
        release_id=RELEASE_ID,
        release_name="New.Release.Name",
        size="1 KiB",
        magnet_link=magnet_link,
        torrent_file_url=None,
        info_url="https://tracker.example/details/1",
        seeders=10,
        leechers=1,
        quality="1080p",
        source="RuTracker",
        request_id=REQUEST_ID,
        publish_date=datetime(2026, 2, 1, tzinfo=UTC),
    )


class FakeReleaseRepository(UnusedReleaseRepositoryCalls):
    def __init__(self, releases: list[ReleaseRecord]) -> None:
        self.releases = releases
        self.updates: list[tuple[str, dict[str, object]]] = []

    async def get_releases_for_requests(self, request_ids: list[str]) -> list[ReleaseRecord]:
        return list(self.releases)

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        self.updates.append((release_id, kwargs))
        # Applied, not just recorded: the use case reads the rows back between
        # passes, so a fake that only remembers the call would hide exactly the
        # staleness those reads exist to avoid.
        for release in self.releases:
            if release.id == release_id:
                for name, value in kwargs.items():
                    setattr(release, name, value)
        return True


class FakeSearchService:
    def __init__(
        self,
        match: ReleaseSearchResultRecord | None = None,
        *,
        error: Exception | None = None,
        is_configured: bool = True,
    ) -> None:
        self._match = match
        self._error = error
        self.is_configured = is_configured
        self.queries: list[str] = []

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        self.queries.append(query)
        if self._error is not None:
            raise self._error
        results = [self._match] if self._match else []
        return ReleaseSearchResults(results=results, query=query, total_results=len(results))

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._match

    async def fetch_torrent(self, url: str) -> bytes:
        raise AssertionError("not used in this test")


class FakeDownloadService(UnusedReleaseDownloadCalls):
    def __init__(
        self,
        states: dict[str, ReleaseTorrentState] | None = None,
        *,
        is_configured: bool = True,
    ) -> None:
        self.states = states or {}
        self.is_configured = is_configured
        self.downloads: list[str] = []
        self.looked_up: list[str] = []

    async def get_torrent_state(self, info_hash: str) -> ReleaseTorrentState | None:
        self.looked_up.append(info_hash.upper())
        return self.states.get(info_hash.upper())

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        self.downloads.append(release_id)
        return QueuedDownload(
            operation="download",
            status="queued",
            operation_id=None,
            location=None,
            message=None,
            resource_id=release_id,
            details=None,
        )


class FakeIndexerDirectory(UnusedIndexerDirectoryCalls):
    def __init__(self, indexers: list[IndexerRecord] | None = None) -> None:
        self._indexers = indexers or []
        self.is_configured = True

    async def list_indexers(self) -> list[IndexerRecord]:
        return list(self._indexers)


class FakeRequestRepository(UnusedMediaRequestCalls):
    def __init__(self, record: MediaRequestRecord | None) -> None:
        self._record = record

    async def get_request(self, request_id: str) -> MediaRequestRecord | None:
        return self._record


@dataclass(slots=True)
class Harness:
    use_case: RefreshRequestReleasesUseCase
    repository: FakeReleaseRepository
    search: FakeSearchService
    download: FakeDownloadService
    warnings: Any
    recompute: Any

    async def refresh(self, scope: RequestScope | None = None) -> ReleaseRefreshDTO:
        return await self.use_case.execute(
            RefreshRequestReleasesCommand(
                request_id=REQUEST_ID,
                scope=scope or RequestScope.unrestricted(),
            )
        )


def build_harness(
    releases: list[ReleaseRecord],
    *,
    match: ReleaseSearchResultRecord | None = None,
    search_error: Exception | None = None,
    states: dict[str, ReleaseTorrentState] | None = None,
    owner_user_id: str | None = OWNER_ID,
    download_configured: bool = True,
    search_configured: bool = True,
    request_found: bool = True,
) -> Harness:
    repository = FakeReleaseRepository(releases)
    search = FakeSearchService(match, error=search_error, is_configured=search_configured)
    download = FakeDownloadService(states, is_configured=download_configured)
    warnings = stub_warning_repository()
    recompute = stub_recompute_state()

    regrapper = ReleaseRegrapper(
        repository=repository,
        search_service=search,
        download_service=download,
        warning_repository=warnings,
        recompute_state=recompute,
        directory=FakeIndexerDirectory(),
    )

    request_repository = FakeRequestRepository(
        replace(make_record(REQUEST_ID), owner_user_id=owner_user_id) if request_found else None
    )

    use_case = RefreshRequestReleasesUseCase(
        request_repository=request_repository,
        release_repository=repository,
        warning_repository=warnings,
        download_service=download,
        search_service=search,
        regrapper=regrapper,
        recompute_state=recompute,
    )

    return Harness(
        use_case=use_case,
        repository=repository,
        search=search,
        download=download,
        warnings=warnings,
        recompute=recompute,
    )


async def test_a_release_in_flight_picks_up_what_the_client_reports() -> None:
    release = make_release()
    moved = state_for(
        release,
        progress=42.0,
        download_speed=2048.0,
        status=ReleaseStatus.DOWNLOADING,
    )

    harness = build_harness([release], states={release.info_hash: moved})
    dto = await harness.refresh()

    assert dto.statuses_updated == 1
    assert dto.regrabbed == 0
    assert [release.id for release in dto.releases] == [RELEASE_ID]
    assert harness.repository.updates == [
        (
            RELEASE_ID,
            {
                "progress": 42.0,
                "download_speed": 2048.0,
                "upload_speed": 0.0,
                "seeders": 1,
                "leechers": 0,
                "ratio": 1.0,
                "size_bytes": 1024,
                "status": ReleaseStatus.DOWNLOADING,
                "completed_at": release.completed_at,
            },
        )
    ]


async def test_an_unchanged_torrent_is_left_alone() -> None:
    release = make_release()

    harness = build_harness([release], states={release.info_hash: state_for(release)})
    dto = await harness.refresh()

    assert dto.statuses_updated == 0
    assert harness.repository.updates == []


async def test_a_torrent_the_client_does_not_know_is_left_alone() -> None:
    harness = build_harness([make_release()])
    dto = await harness.refresh()

    assert dto.statuses_updated == 0
    assert harness.repository.updates == []


async def test_completion_is_stamped_once_and_not_revised_by_a_later_read() -> None:
    release = make_release(status=ReleaseStatus.DOWNLOADING, progress=99.0)
    finished = state_for(release, progress=100.0, status=ReleaseStatus.COMPLETED)

    harness = build_harness([release], states={release.info_hash: finished})
    await harness.refresh()

    _, fields = harness.repository.updates[0]
    assert fields["status"] is ReleaseStatus.COMPLETED
    assert fields["completed_at"] == release.completed_at


async def test_a_finished_release_is_downloaded_again_when_its_hash_moved() -> None:
    release = make_release(status=ReleaseStatus.COMPLETED, info_hash="OLDHASH", progress=100.0)

    harness = build_harness([release], match=make_match())
    dto = await harness.refresh()

    assert dto.regrabbed == 1
    assert harness.download.downloads == [RELEASE_ID]
    assert harness.repository.updates == [
        (
            RELEASE_ID,
            {
                "info_hash": "NEWHASH",
                "export_failures_count": 0,
                "last_exported_info_hash": None,
                "name": "New.Release.Name",
                "info_url": "https://tracker.example/details/1",
                "published_at": datetime(2026, 2, 1, tzinfo=UTC),
                "status": ReleaseStatus.DOWNLOADING,
                "progress": 0.0,
                "completed_at": None,
            },
        )
    ]


async def test_a_re_grabbed_release_has_its_status_read_back_from_the_client() -> None:
    release = make_release(status=ReleaseStatus.COMPLETED, info_hash="OLDHASH", progress=100.0)
    replaced = state_for(release, progress=3.0, status=ReleaseStatus.DOWNLOADING)

    harness = build_harness([release], match=make_match(), states={"NEWHASH": replaced})
    dto = await harness.refresh()

    # The row now carries the replacement's hash, so that is the torrent the
    # status has to be reported for - not the one the refresh started with.
    assert harness.download.looked_up == ["NEWHASH"]
    assert harness.repository.updates[-1][1]["progress"] == 3.0
    assert dto.regrabbed == 1
    assert dto.statuses_updated == 1


async def test_an_unchanged_hash_is_not_downloaded_again() -> None:
    release = make_release(status=ReleaseStatus.COMPLETED, info_hash="SAMEHASH")

    harness = build_harness([release], match=make_match("magnet:?xt=urn:btih:SAMEHASH"))
    dto = await harness.refresh()

    assert dto.regrabbed == 0
    assert harness.download.downloads == []


async def test_a_hand_supplied_release_is_never_re_grabbed() -> None:
    release = make_release(status=ReleaseStatus.COMPLETED, torrent_source="manual")

    harness = build_harness([release], match=make_match())
    dto = await harness.refresh()

    assert dto.regrabbed == 0
    assert harness.search.queries == []
    assert harness.download.downloads == []


async def test_a_release_still_in_flight_is_not_looked_up_again() -> None:
    release = make_release(status=ReleaseStatus.DOWNLOADING, torrent_source="RuTracker")
    unchanged = {release.info_hash: state_for(release)}

    harness = build_harness([release], match=make_match(), states=unchanged)
    await harness.refresh()

    assert harness.search.queries == []


async def test_an_unreachable_indexer_warns_and_does_not_fail_the_refresh() -> None:
    finished = make_release(release_id="rel-finished", status=ReleaseStatus.COMPLETED)
    moving = make_release(release_id="rel-moving", status=ReleaseStatus.DOWNLOADING, progress=10.0)

    harness = build_harness(
        [finished, moving],
        search_error=ReleaseSearchUnavailableError("indexer banned"),
        states={moving.info_hash: state_for(moving, progress=55.0)},
    )
    dto = await harness.refresh()

    assert dto.regrabbed == 0
    assert dto.statuses_updated == 1
    harness.warnings.replace_for_releases.assert_awaited()


async def test_the_request_is_settled_after_the_status_pass() -> None:
    release = make_release(status=ReleaseStatus.DOWNLOADING, progress=10.0)

    harness = build_harness(
        [release], states={release.info_hash: state_for(release, progress=55.0)}
    )
    await harness.refresh()

    harness.recompute.execute.assert_awaited_once_with([REQUEST_ID])


async def test_a_request_outside_the_callers_scope_is_a_not_found() -> None:
    release = make_release(status=ReleaseStatus.COMPLETED)

    harness = build_harness([release], match=make_match(), owner_user_id=OWNER_ID)

    with pytest.raises(MediaRequestNotFoundError):
        await harness.refresh(RequestScope.owned_by("someone-else"))

    assert harness.search.queries == []
    assert harness.download.downloads == []


async def test_an_unknown_request_is_a_not_found() -> None:
    harness = build_harness([], request_found=False)

    with pytest.raises(MediaRequestNotFoundError):
        await harness.refresh()


async def test_qbittorrent_is_required() -> None:
    harness = build_harness([make_release()], download_configured=False)

    with pytest.raises(QbittorrentNotConfiguredError):
        await harness.refresh()


async def test_prowlarr_is_required() -> None:
    harness = build_harness([make_release()], search_configured=False)

    with pytest.raises(ProwlarrNotConfiguredError):
        await harness.refresh()
