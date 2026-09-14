"""Tests for re-grabbing releases the indexer has since replaced."""

from __future__ import annotations

from datetime import UTC, datetime

from src.application.interfaces.releases import (
    QueuedDownload,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
)
from src.application.use_cases.releases.regrab_outdated import RegrabOutdatedReleasesUseCase
from src.domain.enums import ReleaseStatus

RELEASE_ID = "https://tracker.example/details/1"


def make_release(*, name: str = "Old.Release.Name", info_hash: str = "OLDHASH") -> ReleaseRecord:
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
        request_ids=["req-1"],
        requests=[],
        torrent_source="prowlarr",
        quality="1080p",
        files=[],
        last_exported_info_hash=None,
        export_failures_count=0,
        info_url="https://tracker.example/details/1",
    )


def make_match(
    *,
    magnet_link: str | None = "magnet:?xt=urn:btih:NEWHASH",
    release_name: str = "New.Release.Name",
    info_url: str | None = "https://tracker.example/details/1-updated",
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
    def __init__(self, match: ReleaseSearchResultRecord | None) -> None:
        self._match = match
        self.queries: list[str] = []

    async def search(self, query: str, request_id: str | None = None) -> ReleaseSearchResults:
        self.queries.append(query)
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
