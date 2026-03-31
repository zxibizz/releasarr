"""Unit tests for release use cases."""

from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime

import pytest

from src.application.interfaces.releases import (
    CreateReleaseData,
    FileMappingUpdateData,
    QueuedDownload,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
)
from src.application.use_cases.releases.commands import (
    CreateReleaseCommand,
    FileMappingCommand,
    ListReleasesOptions,
    QueueReleaseDownloadCommand,
    SearchReleaseSourcesCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.create_release import CreateReleaseUseCase
from src.application.use_cases.releases.delete_release import DeleteReleaseUseCase
from src.application.use_cases.releases.get_release import GetReleaseUseCase
from src.application.use_cases.releases.list_releases import ListReleasesUseCase
from src.application.use_cases.releases.pause_release import PauseReleaseUseCase
from src.application.use_cases.releases.queue_release_download import QueueReleaseDownloadUseCase
from src.application.use_cases.releases.resume_release import ResumeReleaseUseCase
from src.application.use_cases.releases.search_release_sources import SearchReleaseSourcesUseCase
from src.application.use_cases.releases.update_file_mappings import UpdateReleaseFileMappingsUseCase
from src.application.use_cases.releases.exceptions import (
    ReleaseActionNotAllowedError,
    ReleaseDownloadConflictError,
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.domain.enums import MediaType, ReleaseStatus
from src.settings.config import AppSettings


def make_release_file(
    file_id: str,
    *,
    mapping: ReleaseFileMapping | None = None,
    name: str | None = None,
) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=name or f"file-{file_id}.mkv",
        size_bytes=2048,
        path=f"/downloads/{file_id}.mkv",
        mapping=mapping,
    )


def make_release_record(
    release_id: str,
    *,
    request_ids: list[str] | None = None,
    files: list[ReleaseFileRecord] | None = None,
    status: ReleaseStatus = ReleaseStatus.PENDING,
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id=release_id,
        name=f"Release {release_id}",
        info_hash=f"hash-{release_id}",
        size_bytes=1024,
        status=status,
        progress=0.5,
        download_speed=1.2,
        upload_speed=0.8,
        seeders=10,
        leechers=5,
        ratio=1.0,
        added_at=now,
        completed_at=None,
        request_ids=request_ids or [],
        torrent_source="indexer",
        quality="1080p",
        files=files or [],
    )


class FakeReleaseRepository:
    def __init__(self, releases: dict[str, ReleaseRecord] | None = None) -> None:
        self.releases = releases or {}
        self.last_list_call: dict[str, object] | None = None
        self.last_created: CreateReleaseData | None = None
        self.last_updates: list[FileMappingUpdateData] | None = None
        self.last_deleted: str | None = None

    async def list_releases(
        self,
        *,
        page: int,
        per_page: int,
        status: ReleaseStatus | None,
        request_id: str | None,
    ) -> tuple[list[ReleaseRecord], int]:
        self.last_list_call = {
            "page": page,
            "per_page": per_page,
            "status": status,
            "request_id": request_id,
        }
        items = list(self.releases.values())
        if status is not None:
            items = [item for item in items if item.status == status]
        if request_id is not None:
            items = [item for item in items if request_id in item.request_ids]

        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end], total

    async def create_release(self, data: CreateReleaseData) -> ReleaseRecord:
        self.last_created = data
        release_id = f"rel-{len(self.releases) + 1}"
        record = make_release_record(release_id, request_ids=list(data.request_ids))
        self.releases[release_id] = record
        return record

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        return self.releases.get(release_id)

    async def delete_release(self, release_id: str) -> bool:
        self.last_deleted = release_id
        return self.releases.pop(release_id, None) is not None

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        record = self.releases.get(release_id)
        if record is None:
            return False

        file_lookup = OrderedDict((file_record.id, file_record) for file_record in record.files)
        for update in updates:
            if update.file_id in file_lookup:
                file_lookup[update.file_id].mapping = update.mapping
        self.last_updates = updates
        return True


class FakeLifecycleService:
    def __init__(self, *, pause_result: bool = True, resume_result: bool = True) -> None:
        self.pause_result = pause_result
        self.resume_result = resume_result
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []

    async def pause(self, release_id: str) -> bool:
        self.pause_calls.append(release_id)
        return self.pause_result

    async def resume(self, release_id: str) -> bool:
        self.resume_calls.append(release_id)
        return self.resume_result


class FakeDownloadService:
    def __init__(self, queued: QueuedDownload | None = None) -> None:
        self.queued = queued or QueuedDownload(
            operation="queue_download",
            status="accepted",
            operation_id="op-1",
            location="http://example.test/ops/op-1",
            message=None,
            resource_id="rel-1",
            details={"request_id": "req-1"},
        )
        self.calls: list[tuple[str, str]] = []

    async def queue_download(self, request_id: str, release_id: str) -> QueuedDownload:
        self.calls.append((request_id, release_id))
        return self.queued


class FakeSearchService:
    def __init__(self, results: ReleaseSearchResults) -> None:
        self.results = results
        self.calls: list[tuple[str, str | None]] = []

    async def search(self, query: str, request_id: str | None = None) -> ReleaseSearchResults:
        self.calls.append((query, request_id))
        return self.results


@pytest.mark.asyncio
async def test_list_releases_uses_settings_defaults() -> None:
    releases = {
        release.id: release
        for release in [
            make_release_record(f"rel-{index}", request_ids=[f"req-{index}"], files=[make_release_file(f"file-{index}")])
            for index in range(1, 7)
        ]
    }
    repository = FakeReleaseRepository(releases)
    settings = AppSettings(default_page=2, default_page_size=5, max_page_size=50)
    use_case = ListReleasesUseCase(repository, settings=settings)

    result = await use_case.execute()

    assert repository.last_list_call == {
        "page": 2,
        "per_page": 5,
        "status": None,
        "request_id": None,
    }
    assert result.page == 2
    assert result.per_page == 5
    assert result.total == 6
    assert len(result.releases) == 1
    assert result.releases[0].id == "rel-6"


@pytest.mark.asyncio
async def test_list_releases_applies_filters() -> None:
    release_a = make_release_record("rel-1", status=ReleaseStatus.DOWNLOADING, request_ids=["req-1"])
    release_b = make_release_record("rel-2", status=ReleaseStatus.COMPLETED, request_ids=["req-2"])
    repository = FakeReleaseRepository({release_a.id: release_a, release_b.id: release_b})
    use_case = ListReleasesUseCase(repository, settings=AppSettings())

    options = ListReleasesOptions(status=ReleaseStatus.COMPLETED, request_id="req-2")
    result = await use_case.execute(options)

    assert result.total == 1
    assert result.releases[0].id == release_b.id
    assert repository.last_list_call == {
        "page": 1,
        "per_page": 20,
        "status": ReleaseStatus.COMPLETED,
        "request_id": "req-2",
    }


@pytest.mark.asyncio
async def test_get_release_not_found_raises() -> None:
    use_case = GetReleaseUseCase(FakeReleaseRepository())

    with pytest.raises(ReleaseNotFoundError):
        await use_case.execute("missing")


@pytest.mark.asyncio
async def test_create_release_deduplicates_request_ids() -> None:
    repository = FakeReleaseRepository()
    use_case = CreateReleaseUseCase(repository)
    command = CreateReleaseCommand(
        magnet_link="magnet:?xt=urn:btih:test",
        request_ids=["req-1", "req-1", "req-2", ""],
    )

    dto = await use_case.execute(command)

    assert dto.request_ids == ["req-1", "req-2"]
    assert repository.last_created is not None
    assert repository.last_created.request_ids == ["req-1", "req-2"]


@pytest.mark.asyncio
async def test_create_release_requires_request_id() -> None:
    repository = FakeReleaseRepository()
    use_case = CreateReleaseUseCase(repository)

    command = CreateReleaseCommand(magnet_link="magnet:?xt=urn:btih:test", request_ids=[])

    with pytest.raises(ValueError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_delete_release_not_found_raises() -> None:
    repository = FakeReleaseRepository()
    use_case = DeleteReleaseUseCase(repository)

    with pytest.raises(ReleaseNotFoundError):
        await use_case.execute("rel-unknown")


@pytest.mark.asyncio
async def test_update_file_mappings_validates_file_presence() -> None:
    release = make_release_record("rel-1", files=[make_release_file("file-1")])
    repository = FakeReleaseRepository({release.id: release})
    use_case = UpdateReleaseFileMappingsUseCase(repository)
    command = UpdateFileMappingsCommand(
        release_id="rel-1",
        files=[
            FileMappingCommand(
                file_id="missing",
                mapping_type=MediaType.MOVIE.value,
                request_id="req-1",
            )
        ],
    )

    with pytest.raises(ReleaseFileNotFoundError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_update_file_mappings_updates_movie_mapping() -> None:
    file_record = make_release_file("file-1")
    release = make_release_record("rel-1", files=[file_record])
    repository = FakeReleaseRepository({release.id: release})
    use_case = UpdateReleaseFileMappingsUseCase(repository)
    command = UpdateFileMappingsCommand(
        release_id="rel-1",
        files=[
            FileMappingCommand(
                file_id="file-1",
                mapping_type=MediaType.MOVIE.value,
                request_id="req-1",
                request_title="Example Movie",
            )
        ],
    )

    result = await use_case.execute(command)

    assert result is True
    assert file_record.mapping is not None
    assert file_record.mapping.mapping_type is MediaType.MOVIE
    assert file_record.mapping.request_id == "req-1"


@pytest.mark.asyncio
async def test_update_file_mappings_requires_series_metadata() -> None:
    file_record = make_release_file("file-1")
    release = make_release_record("rel-1", files=[file_record])
    repository = FakeReleaseRepository({release.id: release})
    use_case = UpdateReleaseFileMappingsUseCase(repository)
    command = UpdateFileMappingsCommand(
        release_id="rel-1",
        files=[
            FileMappingCommand(
                file_id="file-1",
                mapping_type=MediaType.SERIES.value,
                request_id="req-1",
            )
        ],
    )

    with pytest.raises(ValueError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_pause_release_returns_async_operation() -> None:
    release = make_release_record("rel-1")
    repository = FakeReleaseRepository({release.id: release})
    lifecycle_service = FakeLifecycleService()
    use_case = PauseReleaseUseCase(repository, lifecycle_service)

    result = await use_case.execute("rel-1")

    assert result.operation == "pause_release"
    assert result.status == "accepted"
    assert lifecycle_service.pause_calls == ["rel-1"]


@pytest.mark.asyncio
async def test_pause_release_raises_when_service_declines() -> None:
    release = make_release_record("rel-1")
    repository = FakeReleaseRepository({release.id: release})
    lifecycle_service = FakeLifecycleService(pause_result=False)
    use_case = PauseReleaseUseCase(repository, lifecycle_service)

    with pytest.raises(ReleaseActionNotAllowedError):
        await use_case.execute("rel-1")


@pytest.mark.asyncio
async def test_resume_release_raises_when_not_found() -> None:
    repository = FakeReleaseRepository()
    lifecycle_service = FakeLifecycleService()
    use_case = ResumeReleaseUseCase(repository, lifecycle_service)

    with pytest.raises(ReleaseNotFoundError):
        await use_case.execute("rel-missing")


@pytest.mark.asyncio
async def test_queue_release_download_conflict() -> None:
    release = make_release_record("rel-1", request_ids=["req-1"])
    repository = FakeReleaseRepository({release.id: release})
    download_service = FakeDownloadService()
    use_case = QueueReleaseDownloadUseCase(repository, download_service)

    command = QueueReleaseDownloadCommand(request_id="req-2", release_id="rel-1")
    with pytest.raises(ReleaseDownloadConflictError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_queue_release_download_returns_operation() -> None:
    release = make_release_record("rel-1", request_ids=["req-1"])
    repository = FakeReleaseRepository({release.id: release})
    download_service = FakeDownloadService()
    use_case = QueueReleaseDownloadUseCase(repository, download_service)

    command = QueueReleaseDownloadCommand(request_id="req-1", release_id="rel-1")
    result = await use_case.execute(command)

    assert result.operation == "queue_download"
    assert download_service.calls == [("req-1", "rel-1")]


@pytest.mark.asyncio
async def test_search_release_sources_maps_results() -> None:
    results = ReleaseSearchResults(
        results=[
            ReleaseSearchResultRecord(
                release_id="rel-1",
                release_name="Test Release",
                size="1 GB",
                magnet_link="magnet:?xt=urn:btih:test",
                torrent_file_url=None,
                info_url="http://example.test",
                seeders=10,
                leechers=2,
                quality="1080p",
                source="indexer",
                request_id="req-1",
            )
        ],
        query="test",
        total_results=1,
    )
    search_service = FakeSearchService(results)
    use_case = SearchReleaseSourcesUseCase(search_service)
    command = SearchReleaseSourcesCommand(query="test", request_id="req-1")

    response = await use_case.execute(command)

    assert response.total_results == 1
    assert response.results[0].release_id == "rel-1"
    assert search_service.calls == [("test", "req-1")]


@pytest.mark.asyncio
async def test_delete_release_removes_record() -> None:
    release = make_release_record("rel-1")
    repository = FakeReleaseRepository({release.id: release})
    use_case = DeleteReleaseUseCase(repository)

    await use_case.execute("rel-1")

    assert "rel-1" not in repository.releases
    assert repository.last_deleted == "rel-1"
