"""Tests for re-grabbing releases the indexer has since replaced."""

from __future__ import annotations

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

RELEASE_ID = "https://tracker.example/details/1"


def make_release(
    *,
    name: str = "Old.Release.Name",
    info_hash: str = "OLDHASH",
    request_ids: list[str] | None = None,
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id=RELEASE_ID,
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
        torrent_source="RuTracker",
        quality="1080p",
        files=[],
        last_exported_info_hash=None,
        export_failures_count=0,
        info_url="https://tracker.example/details/1",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
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


class FakeReleaseRepository:
    def __init__(self, release: ReleaseRecord) -> None:
        self.release = release
        self.updates: dict[str, object] = {}

    async def get_potential_outdated_releases(self) -> list[ReleaseRecord]:
        return [self.release]

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        self.updates.update(kwargs)
        return True


class FakeSearchService:
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


class FakeDownloadService:
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


async def test_regrab_updates_name_and_info_url_when_hash_changed() -> None:
    release = make_release()
    match = make_match()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()

    use_case = RegrabOutdatedReleasesUseCase(repository, search_service, download_service)
    await use_case.execute()

    assert repository.updates["name"] == match.release_name
    assert repository.updates["info_url"] == match.info_url
    assert repository.updates["published_at"] == match.publish_date
    assert repository.updates["info_hash"] == "NEWHASH"
    assert len(download_service.calls) == 1


async def test_regrab_does_not_redownload_when_hash_unchanged() -> None:
    release = make_release(info_hash="SAMEHASH")
    match = make_match(magnet_link="magnet:?xt=urn:btih:SAMEHASH")
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()

    use_case = RegrabOutdatedReleasesUseCase(repository, search_service, download_service)
    await use_case.execute()

    assert repository.updates == {}
    assert download_service.calls == []


async def test_regrab_skips_releases_with_no_matching_indexer_result() -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None)
    download_service = FakeDownloadService()

    use_case = RegrabOutdatedReleasesUseCase(repository, search_service, download_service)
    await use_case.execute()

    assert repository.updates == {}
    assert download_service.calls == []


class FakeIndexerDirectory:
    def __init__(
        self,
        indexers: list[IndexerRecord],
        *,
        error: Exception | None = None,
    ) -> None:
        self._indexers = indexers
        self._error = error

    async def list_indexers(self) -> list[IndexerRecord]:
        if self._error is not None:
            raise self._error
        return self._indexers

    async def list_history(self, **kwargs: object) -> object:
        raise AssertionError("not used in this test")

    async def list_logs(self, **kwargs: object) -> object:
        raise AssertionError("not used in this test")

    async def test_indexer(self, indexer_id: int) -> object:
        raise AssertionError("not used in this test")

    async def test_all_indexers(self) -> object:
        raise AssertionError("not used in this test")


async def test_regrab_scopes_search_to_the_releases_own_indexer() -> None:
    release = make_release()  # torrent_source="RuTracker"
    match = make_match()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory(
        [IndexerRecord(indexer_id=7, name="RuTracker", enabled=True, supports_search=True)]
    )

    use_case = RegrabOutdatedReleasesUseCase(
        repository, search_service, download_service, directory=directory
    )
    await use_case.execute()

    assert search_service.indexer_ids == [7]
    assert len(download_service.calls) == 1


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

    use_case = RegrabOutdatedReleasesUseCase(
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

    use_case = RegrabOutdatedReleasesUseCase(
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


async def test_regrab_falls_back_to_unscoped_search_when_indexer_unknown() -> None:
    release = make_release()  # torrent_source="RuTracker"
    match = make_match()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory(
        [IndexerRecord(indexer_id=9, name="SomeOtherIndexer", enabled=True, supports_search=True)]
    )

    use_case = RegrabOutdatedReleasesUseCase(
        repository, search_service, download_service, directory=directory
    )
    await use_case.execute()

    assert search_service.indexer_ids == [None]


async def test_regrab_falls_back_to_unscoped_search_when_directory_fails() -> None:
    release = make_release()
    match = make_match()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()
    directory = FakeIndexerDirectory([], error=RuntimeError("prowlarr unreachable"))

    use_case = RegrabOutdatedReleasesUseCase(
        repository, search_service, download_service, directory=directory
    )
    await use_case.execute()

    assert search_service.indexer_ids == [None]
    assert len(download_service.calls) == 1


async def test_regrab_warns_the_request_when_the_indexer_is_unavailable(
    captured_records: list[dict[str, Any]],
) -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()

    use_case = RegrabOutdatedReleasesUseCase(repository, search_service, download_service)
    await use_case.execute()

    warnings = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert warnings, "an unavailable indexer produced no log entry bound to the request"
    assert warnings[0]["level"] == "WARNING"
    assert "indexer banned" in warnings[0]["error"]
    assert repository.updates == {}
    assert download_service.calls == []


async def test_regrab_warns_every_request_sharing_the_release() -> None:
    release = make_release(request_ids=["req-1", "req-2"])
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()

    logged_request_ids: list[str] = []
    use_case = RegrabOutdatedReleasesUseCase(
        repository,
        search_service,
        download_service,
        logger=_CollectingLogger(logged_request_ids),  # type: ignore[arg-type]
    )
    await use_case.execute()

    assert logged_request_ids == ["req-1", "req-2"]


class _CollectingLogger:
    """Minimal stand-in recording only the `request_id` kwarg of each warning call."""

    def __init__(self, sink: list[str]) -> None:
        self._sink = sink

    def warning(self, message: str, **kwargs: Any) -> None:
        self._sink.append(kwargs["request_id"])

    def opt(self, **kwargs: Any) -> _CollectingLogger:
        return self

    def error(self, message: str, **kwargs: Any) -> None:
        raise AssertionError("unexpected error-level log for an indexer-unavailable regrab")


class FakeRequestWarningRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, list[str], list[Any]]] = []

    async def replace_for_releases(
        self, code: Any, release_ids: list[str], warnings: list[Any]
    ) -> None:
        self.calls.append((code, list(release_ids), list(warnings)))

    async def replace_for_requests(
        self, code: Any, request_ids: list[str], warnings: list[Any]
    ) -> None:
        raise AssertionError("not used in this test")

    async def delete_for_release(self, release_id: str) -> None:
        raise AssertionError("not used in this test")

    async def delete_for_request_release(self, request_id: str, release_id: str) -> None:
        raise AssertionError("not used in this test")

    async def list_for_requests(self, request_ids: list[str]) -> dict[str, list[Any]]:
        raise AssertionError("not used in this test")

    async def list_for_releases(self, release_ids: list[str]) -> dict[str, list[Any]]:
        raise AssertionError("not used in this test")


async def test_regrab_persists_a_warning_row_when_the_indexer_is_unavailable() -> None:
    release = make_release()
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(None, error=ReleaseSearchUnavailableError("indexer banned"))
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()

    use_case = RegrabOutdatedReleasesUseCase(
        repository, search_service, download_service, warning_repository=warning_repository
    )
    await use_case.execute()

    assert len(warning_repository.calls) == 1
    code, release_ids, rows = warning_repository.calls[0]
    assert code is RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE
    assert release_ids == [RELEASE_ID]
    assert [row.request_id for row in rows] == ["req-1"]
    assert rows[0].details == {"reason": "indexer banned"}


async def test_regrab_clears_the_warning_row_on_a_valid_search_response() -> None:
    """A release that regains a response is cleared, even if nothing else changed."""

    release = make_release(info_hash="SAMEHASH")
    match = make_match(magnet_link="magnet:?xt=urn:btih:SAMEHASH")
    repository = FakeReleaseRepository(release)
    search_service = FakeSearchService(match)
    download_service = FakeDownloadService()
    warning_repository = FakeRequestWarningRepository()

    use_case = RegrabOutdatedReleasesUseCase(
        repository, search_service, download_service, warning_repository=warning_repository
    )
    await use_case.execute()

    assert len(warning_repository.calls) == 1
    code, release_ids, rows = warning_repository.calls[0]
    assert code is RequestWarningCode.REGRAB_INDEXER_UNAVAILABLE
    assert release_ids == [RELEASE_ID]
    assert rows == []
