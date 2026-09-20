"""Tests for re-grabbing releases the indexer has since replaced."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from src.application.interfaces.indexers import IndexerRecord
from src.application.interfaces.releases import (
    QueuedDownload,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchUnavailableError,
)
from src.application.use_cases.releases.regrab_outdated import RegrabOutdatedReleasesUseCase
from src.domain.enums import ReleaseStatus, RequestWarningCode
from tests.builders import stub_auto_mapper, stub_recompute_state, stub_warning_repository
from tests.fakes import (
    UnusedIndexerDirectoryCalls,
    UnusedReleaseDownloadCalls,
    UnusedReleaseRepositoryCalls,
    UnusedRequestWarningCalls,
)

RELEASE_ID = "https://tracker.example/details/1"
INDEXER_RUTRACKER = IndexerRecord(
    indexer_id=7,
    name="RuTracker",
    enabled=True,
    supports_search=True,
)


def request_check_lines(records: list[dict[str, Any]]) -> list[str]:
    """The lines the check bound to the release's own request.

    A release's activity view is filtered on `request_id`, so a skip that only
    reached the scheduler's log would be invisible where someone would look for
    it.
    """

    return [
        record["message"]
        for record in records
        if record.get("request_id") == "req-1" and record["level"] == "WARNING"
    ]


def make_release(
    *,
    name: str = "Old.Release.Name",
    search_query: str | None = None,
    info_hash: str = "OLDHASH",
    request_ids: list[str] | None = None,
    release_id: str = RELEASE_ID,
    torrent_source: str = "RuTracker",
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id=release_id,
        name=name,
        info_hash=info_hash,
        size_bytes=1024,
        status=ReleaseStatus.COMPLETED,
        progress=1.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=1,
        leechers=0,
        ratio=1.0,
        added_at=now,
        completed_at=now,
        request_ids=request_ids if request_ids is not None else ["req-1"],
        requests=[],
        torrent_source=torrent_source,
        quality="1080p",
        files=[],
        last_exported_info_hash=None,
        export_failures_count=0,
        info_url="https://tracker.example/details/1",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        search_query=search_query,
    )


def make_match(
    *,
    magnet_link: str | None = "magnet:?xt=urn:btih:NEWHASH",
    release_name: str = "New.Release.Name",
    info_url: str | None = "https://tracker.example/details/1-updated",
    publish_date: datetime | None = datetime(2026, 2, 1, tzinfo=UTC),
) -> ReleaseSearchResultRecord:
    return ReleaseSearchResultRecord(
        release_id=RELEASE_ID,
        release_name=release_name,
        size="1 GB",
        magnet_link=magnet_link,
        torrent_file_url=None,
        info_url=info_url,
        seeders=10,
        leechers=1,
        quality="1080p",
        source="prowlarr",
        request_id="req-1",
        publish_date=publish_date,
    )


class FakeReleaseRepository(UnusedReleaseRepositoryCalls):
    def __init__(self, *releases: ReleaseRecord) -> None:
        self.releases = list(releases)
        self.updates: dict[str, object] = {}
        # The sweep stamps every candidate it looked at, which is bookkeeping
        # rather than a re-grab, so it is kept apart from `updates`.
        self.checks: list[tuple[str, object]] = []

    async def get_potential_outdated_releases(self) -> list[ReleaseRecord]:
        return self.releases

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        if set(kwargs) == {"regrab_checked_at"}:
            self.checks.append((release_id, kwargs["regrab_checked_at"]))
        else:
            self.updates.update(kwargs)
        return True


class RecordingSleeper:
    """Records what the pacing asked for instead of waiting for it."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


class FakeSearchService:
    is_configured = True

    def __init__(
        self,
        match: ReleaseSearchResultRecord | None,
        *,
        error: Exception | None = None,
    ) -> None:
        self._match = match
        self._error = error
        self.queries: list[str] = []
        self.indexer_ids: list[int | None] = []

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        self.queries.append(query)
        self.indexer_ids.append(indexer_id)
        if self._error is not None:
            raise self._error
        results = [self._match] if self._match else []
        return ReleaseSearchResults(results=results, query=query, total_results=len(results))

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._match

    async def fetch_torrent(self, url: str) -> bytes:
        raise AssertionError("not used in this test")


class FakeDownloadService(UnusedReleaseDownloadCalls):
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        self.calls.append(
            {
                "request_id": request_id,
                "release_id": release_id,
                "magnet_link": magnet_link,
            }
        )
        return QueuedDownload(
            operation="download",
            status="queued",
            operation_id=None,
            location=None,
            message=None,
            resource_id=None,
            details=None,
        )


def build_use_case(
    repository: FakeReleaseRepository,
    search_service: FakeSearchService,
    download_service: FakeDownloadService,
    **overrides: Any,
) -> RegrabOutdatedReleasesUseCase:
    overrides.setdefault("auto_mapper", stub_auto_mapper())
    overrides.setdefault("warning_repository", stub_warning_repository())
    overrides.setdefault("recompute_state", stub_recompute_state())
    # A directory that knows the release's own tracker, so a test that is not
    # about scoping is not quietly exercising the skip path.
    overrides.setdefault("directory", FakeIndexerDirectory([INDEXER_RUTRACKER]))
    return RegrabOutdatedReleasesUseCase(repository, search_service, download_service, **overrides)


async def test_regrab_updates_name_and_info_url_when_hash_changed() -> None:
    release = make_release()
    match = make_match()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()

    use_case = build_use_case(repository, search_service, download_service)
    await use_case.execute()

    assert repository.updates["name"] == match.release_name
    assert repository.updates["info_url"] == match.info_url
    assert repository.updates["published_at"] == match.publish_date
    assert repository.updates["info_hash"] == "NEWHASH"
    # The replacement is a fresh download, so the release cannot go on counting
    # as finished while its files are being replaced.
    assert repository.updates["status"] == ReleaseStatus.DOWNLOADING
    assert repository.updates["progress"] == 0.0
    assert repository.updates["completed_at"] is None
    assert len(download_service.calls) == 1


async def test_regrab_does_not_redownload_when_hash_unchanged() -> None:
    release = make_release(info_hash="SAMEHASH")
    match = make_match(magnet_link="magnet:?xt=urn:btih:SAMEHASH")
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()

    use_case = build_use_case(repository, search_service, download_service)
    await use_case.execute()

    assert repository.updates == {}
    assert download_service.calls == []


async def test_regrab_warns_when_the_release_is_no_longer_listed() -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None)
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()

    use_case = build_use_case(
        repository, search_service, download_service, warning_repository=warning_repository
    )
    await use_case.execute()

    assert repository.updates == {}
    assert download_service.calls == []
    release_ids, rows = calls_by_code(warning_repository)[RequestWarningCode.RELEASE_NOT_LISTED]
    assert release_ids == [RELEASE_ID]
    assert [row.request_id for row in rows] == ["req-1"]
    assert rows[0].details == {"indexer": "RuTracker"}


class FakeIndexerDirectory(UnusedIndexerDirectoryCalls):
    def __init__(
        self,
        indexers: list[IndexerRecord],
        *,
        error: Exception | None = None,
        is_configured: bool = True,
    ) -> None:
        self._indexers = indexers
        self._error = error
        self.is_configured = is_configured

    async def list_indexers(self) -> list[IndexerRecord]:
        if self._error is not None:
            raise self._error
        return self._indexers


async def test_regrab_scopes_search_to_the_releases_own_indexer() -> None:
    release = make_release()  # torrent_source="RuTracker"
    match = make_match()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory(
        [IndexerRecord(indexer_id=7, name="RuTracker", enabled=True, supports_search=True)]
    )

    use_case = build_use_case(repository, search_service, download_service, directory=directory)
    await use_case.execute()

    assert search_service.indexer_ids == [7]
    assert len(download_service.calls) == 1


async def test_regrab_searches_with_the_query_the_release_was_grabbed_with() -> None:
    """The stored query is replayed; the tracker's title is not what found it."""

    release = make_release(name="Long.Tracker.Title.S01E01.1080p.Rus", search_query="Show S01")
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(repository, search_service, download_service)
    await use_case.execute()

    assert search_service.queries == ["Show S01"]


async def test_regrab_falls_back_to_the_release_name_without_a_stored_query() -> None:
    """A release grabbed before the query was recorded is still checked."""

    release = make_release(name="Old.Release.Name")
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(repository, search_service, download_service)
    await use_case.execute()

    assert search_service.queries == ["Old.Release.Name"]


def many_releases(count: int, *, torrent_source: str = "RuTracker") -> list[ReleaseRecord]:
    """A backlog on one tracker, each release named for the one it came from.

    The name is what the check searches with, so a test can assert which of them
    a run took rather than only how many.
    """

    return [
        make_release(
            release_id=f"{torrent_source}-{index:02d}",
            name=f"{torrent_source} {index:02d}",
            torrent_source=torrent_source,
        )
        for index in range(count)
    ]


async def test_a_backlog_that_fits_the_ceiling_goes_in_one_run() -> None:
    """Spreading it would delay a check that costs the tracker the same either way."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    repository = FakeReleaseRepository(*many_releases(12))
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        clock=lambda: now,
        sleeper=RecordingSleeper(),
        max_per_indexer=20,
    )
    result = await use_case.execute()

    assert result.checked == 12
    assert result.deferred == 0


async def test_a_larger_backlog_is_spread_over_the_configured_executions() -> None:
    """Fifty waiting on one tracker, five runs to cover them: ten a run."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    backlog = many_releases(50)
    repository = FakeReleaseRepository(*backlog)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        clock=lambda: now,
        sleeper=RecordingSleeper(),
        max_per_indexer=20,
        spread_executions=5,
    )
    result = await use_case.execute()

    assert result.checked == 10
    assert result.deferred == 40
    # The ones that waited longest go first: the fake returns the list in the
    # order the query would, least recently checked first.
    assert search_service.queries == [release.name for release in backlog[:10]]


async def test_the_ceiling_caps_an_indexers_share() -> None:
    """An even fifth of 200 is 40, which is more than a tracker should be asked."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    repository = FakeReleaseRepository(*many_releases(200))
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        clock=lambda: now,
        sleeper=RecordingSleeper(),
        max_per_indexer=20,
        spread_executions=5,
    )
    result = await use_case.execute()

    assert result.checked == 20
    assert result.deferred == 180


async def test_each_indexer_draws_on_its_own_allowance() -> None:
    """A quiet tracker is not held back by a busy one, and neither spends the other's."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    repository = FakeReleaseRepository(
        *many_releases(30),
        *many_releases(4, torrent_source="OtherTracker"),
    )
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=FakeIndexerDirectory(
            [
                INDEXER_RUTRACKER,
                IndexerRecord(
                    indexer_id=9,
                    name="OtherTracker",
                    enabled=True,
                    supports_search=True,
                ),
            ]
        ),
        clock=lambda: now,
        sleeper=RecordingSleeper(),
        max_per_indexer=20,
        spread_executions=5,
    )
    result = await use_case.execute()

    # RuTracker: ceil(30 / 5) = 6. OtherTracker: 4, which fits its ceiling, so all of it.
    assert result.checked == 10
    assert result.deferred == 24
    taken = Counter(query.split(" ")[0] for query in search_service.queries)
    assert taken == {"RuTracker": 6, "OtherTracker": 4}


async def test_regrab_spaces_checks_against_the_same_indexer() -> None:
    """One tracker, asked twice in a row, is exactly what gets a client throttled."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    repository = FakeReleaseRepository(
        make_release(release_id="rel-1"),
        make_release(release_id="rel-2"),
    )
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    sleeper = RecordingSleeper()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=FakeIndexerDirectory([INDEXER_RUTRACKER]),
        clock=lambda: now,
        indexer_delay_seconds=2.0,
        sleeper=sleeper,
    )
    result = await use_case.execute()

    assert search_service.indexer_ids == [7, 7]
    assert sleeper.waits == [2.0]
    assert result.checked == 2


async def test_regrab_does_not_hold_up_another_indexer() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repository = FakeReleaseRepository(
        make_release(release_id="rel-1"),
        make_release(release_id="rel-2", torrent_source="OtherTracker"),
    )
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    sleeper = RecordingSleeper()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=FakeIndexerDirectory(
            [
                INDEXER_RUTRACKER,
                IndexerRecord(
                    indexer_id=9, name="OtherTracker", enabled=True, supports_search=True
                ),
            ]
        ),
        clock=lambda: now,
        indexer_delay_seconds=2.0,
        sleeper=sleeper,
    )
    await use_case.execute()

    assert search_service.indexer_ids == [7, 9]
    assert sleeper.waits == []


async def test_regrab_marks_every_release_it_looked_at() -> None:
    """The stamp is the rotation: a candidate that never advances holds its slot."""

    now = datetime(2026, 1, 1, tzinfo=UTC)
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=FakeIndexerDirectory([INDEXER_RUTRACKER]),
        clock=lambda: now,
    )
    await use_case.execute()

    assert repository.checks == [(RELEASE_ID, now)]


async def test_regrab_skips_the_search_when_prowlarr_has_blocked_the_indexer() -> None:
    release = make_release()  # torrent_source="RuTracker"
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    directory = FakeIndexerDirectory(
        [
            IndexerRecord(
                indexer_id=7,
                name="RuTracker",
                enabled=True,
                supports_search=True,
                disabled_till=datetime(2026, 1, 1, 1, tzinfo=UTC),
            )
        ]
    )
    warning_repository = FakeRequestWarningRepository()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=directory,
        warning_repository=warning_repository,
        clock=lambda: now,
    )
    await use_case.execute()

    assert search_service.queries == []
    assert download_service.calls == []
    assert len(warning_repository.calls) == 1
    code, release_ids, rows = warning_repository.calls[0]
    assert code is RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE
    assert release_ids == [RELEASE_ID]
    assert "blocked by Prowlarr" in rows[0].details["reason"]


async def test_regrab_warns_when_the_indexer_is_disabled_in_prowlarr() -> None:
    """A cleared enable flag never expires, so it must warn rather than be searched."""

    release = make_release()  # torrent_source="RuTracker"
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory(
        [IndexerRecord(indexer_id=7, name="RuTracker", enabled=False, supports_search=True)]
    )
    warning_repository = FakeRequestWarningRepository()

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=directory,
        warning_repository=warning_repository,
    )
    await use_case.execute()

    assert search_service.queries == []
    assert download_service.calls == []
    code, release_ids, rows = warning_repository.calls[0]
    assert code is RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE
    assert release_ids == [RELEASE_ID]
    assert [row.request_id for row in rows] == ["req-1"]
    assert "disabled in Prowlarr" in rows[0].details["reason"]


async def test_regrab_skips_a_release_whose_indexer_is_gone(
    captured_records: list[dict[str, Any]],
) -> None:
    """Only the release's own tracker is asked, so an unknown one has no query to run."""

    release = make_release()  # torrent_source="RuTracker"
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()
    directory = FakeIndexerDirectory(
        [IndexerRecord(indexer_id=9, name="SomeOtherIndexer", enabled=True, supports_search=True)]
    )

    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        directory=directory,
        warning_repository=warning_repository,
    )
    await use_case.execute()

    assert search_service.queries == []
    assert download_service.calls == []
    # No answer was received, so nothing is warned about: the check is only
    # recorded on the request's activity view.
    assert warning_repository.calls == []
    assert request_check_lines(captured_records) == ["Could not check for updates: indexer unknown"]


async def test_regrab_skips_every_release_when_prowlarr_is_unconfigured(
    captured_records: list[dict[str, Any]],
) -> None:
    """An unconfigured directory has no indexer names to scope a release to."""

    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory([], is_configured=False)

    use_case = build_use_case(repository, search_service, download_service, directory=directory)
    await use_case.execute()

    assert search_service.indexer_ids == []
    assert download_service.calls == []
    assert request_check_lines(captured_records) == ["Could not check for updates: indexer unknown"]


async def test_regrab_skips_every_release_when_the_indexer_list_fails(
    captured_records: list[dict[str, Any]],
) -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(make_match())
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory([], error=RuntimeError("prowlarr unreachable"))

    use_case = build_use_case(repository, search_service, download_service, directory=directory)
    await use_case.execute()

    assert search_service.indexer_ids == []
    assert download_service.calls == []
    assert request_check_lines(captured_records) == ["Could not check for updates: indexer unknown"]


async def test_regrab_warns_the_request_when_the_indexer_is_unavailable(
    captured_records: list[dict[str, Any]],
) -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()

    use_case = build_use_case(repository, search_service, download_service)
    await use_case.execute()

    warnings = [
        record
        for record in captured_records
        if record.get("request_id") == "req-1" and record["level"] == "WARNING"
    ]
    assert warnings, "an unavailable indexer produced no log entry bound to the request"
    assert "indexer banned" in warnings[0]["error"]
    assert repository.updates == {}
    assert download_service.calls == []


async def test_regrab_warns_every_request_sharing_the_release() -> None:
    release = make_release(request_ids=["req-1", "req-2"])
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()

    logged_request_ids: list[str] = []
    use_case = build_use_case(
        repository,
        search_service,
        download_service,
        logger=_CollectingLogger(logged_request_ids),
    )
    await use_case.execute()

    assert logged_request_ids == ["req-1", "req-2"]


class _CollectingLogger:
    """Minimal stand-in recording only the `request_id` kwarg of each warning call."""

    def __init__(self, sink: list[str]) -> None:
        self._sink = sink

    def info(self, message: str, **kwargs: Any) -> None:
        """The check's opening line is info-level; only the warning is under test."""

    def warning(self, message: str, **kwargs: Any) -> None:
        self._sink.append(kwargs["request_id"])

    def opt(self, **kwargs: Any) -> _CollectingLogger:
        return self

    def error(self, message: str, **kwargs: Any) -> None:
        raise AssertionError("unexpected error-level log for an indexer-unavailable regrab")


class FakeRequestWarningRepository(UnusedRequestWarningCalls):
    def __init__(self) -> None:
        self.calls: list[tuple[Any, list[str], list[Any]]] = []

    async def replace_for_releases(
        self, code: Any, release_ids: Sequence[str], warnings: Sequence[Any]
    ) -> None:
        self.calls.append((code, list(release_ids), list(warnings)))

    async def replace_for_requests(
        self, code: Any, request_ids: Sequence[str], warnings: Sequence[Any]
    ) -> None:
        raise AssertionError("not used in this test")

    async def delete_for_release(self, release_id: str) -> None:
        raise AssertionError("not used in this test")

    async def delete_for_request_release(self, request_id: str, release_id: str) -> None:
        raise AssertionError("not used in this test")

    async def list_for_requests(self, request_ids: Sequence[str]) -> dict[str, list[Any]]:
        raise AssertionError("not used in this test")

    async def list_for_releases(self, release_ids: Sequence[str]) -> dict[str, list[Any]]:
        raise AssertionError("not used in this test")


def calls_by_code(
    repository: FakeRequestWarningRepository,
) -> dict[RequestWarningCode, tuple[list[str], list[Any]]]:
    """The release ids and rows each code's last replace left behind, keyed by code.

    One outcome can touch two codes - the indexer-unavailable clear and the
    not-listed write are separate calls, since `replace_for_releases` is
    single-code - so tests index by code rather than by position.
    """

    return {code: (release_ids, rows) for code, release_ids, rows in repository.calls}


async def test_regrab_persists_a_warning_row_when_the_indexer_is_unavailable() -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()

    use_case = build_use_case(
        repository, search_service, download_service, warning_repository=warning_repository
    )
    await use_case.execute()

    assert len(warning_repository.calls) == 1
    code, release_ids, rows = warning_repository.calls[0]
    assert code is RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE
    assert release_ids == [RELEASE_ID]
    assert [row.request_id for row in rows] == ["req-1"]
    assert rows[0].details == {"reason": "indexer banned"}


async def test_regrab_clears_the_warning_rows_on_a_valid_search_response() -> None:
    """A release that regains a response is cleared, even if nothing else changed."""

    release = make_release(info_hash="SAMEHASH")
    match = make_match(magnet_link="magnet:?xt=urn:btih:SAMEHASH")
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()

    use_case = build_use_case(
        repository, search_service, download_service, warning_repository=warning_repository
    )
    await use_case.execute()

    # The search answered and named this release, which settles both codes.
    assert len(warning_repository.calls) == 2
    by_code = calls_by_code(warning_repository)
    for code in (
        RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE,
        RequestWarningCode.RELEASE_NOT_LISTED,
    ):
        release_ids, rows = by_code[code]
        assert release_ids == [RELEASE_ID]
        assert rows == []


async def test_regrab_leaves_the_not_listed_warning_alone_when_the_indexer_cannot_answer() -> None:
    """An indexer that never answered says nothing about whether it still lists the release."""

    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()

    use_case = build_use_case(
        repository, search_service, download_service, warning_repository=warning_repository
    )
    await use_case.execute()

    assert [code for code, _, _ in warning_repository.calls] == [
        RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE
    ]
