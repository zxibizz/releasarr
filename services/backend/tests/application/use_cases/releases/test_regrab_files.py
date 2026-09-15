"""Tests for what a re-grab does with the release's files."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from torrentool.api import Torrent

from src.application.interfaces.indexers import IndexerRecord
from src.application.interfaces.releases import (
    FileMappingUpdateData,
    FileReconciliation,
    QueuedDownload,
    ReleaseFileMapping,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseRequestSnapshot,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
)
from src.application.interfaces.request_warnings import RequestWarningRecord
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.exceptions import ReleaseRegrabRejectedError
from src.application.use_cases.releases.regrab import ReleaseRegrapper
from src.application.utility.file_matcher import ReleaseFileMatcher
from src.domain.enums import MediaType, ReleaseStatus, RequestWarningCode
from tests.builders import stub_media_request_repository, stub_recompute_state
from tests.fakes import (
    UnusedIndexerDirectoryCalls,
    UnusedReleaseDownloadCalls,
    UnusedReleaseRepositoryCalls,
    UnusedRequestWarningCalls,
)

RELEASE_ID = "https://tracker.example/details/1"
ROOT = "Show.S01.1080p.WEB-DL"
REPACK_ROOT = "Show.S01.1080p.REPACK-GRP"
TORRENT_URL = "https://tracker.example/download/1.torrent"


def torrent_for(*names: str, root: str = ROOT) -> bytes:
    """A torrent whose file list is exactly the given names under one root."""

    with TemporaryDirectory() as directory:
        base = Path(directory) / root
        base.mkdir()
        for name in names:
            target = base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"x" * 1024)
        return Torrent.create_from(base).to_string()


def stored_file(file_id: str, path: str, *, episode: int) -> ReleaseFileRecord:
    return ReleaseFileRecord(
        id=file_id,
        name=path,
        size_bytes=4096,
        path=path,
        mapping=ReleaseFileMapping(
            mapping_type=MediaType.SERIES,
            request_id="req-1",
            request_title="Show - Season 1",
            season=1,
            episode=episode,
        ),
    )


def season_request() -> ReleaseRequestSnapshot:
    return ReleaseRequestSnapshot(
        id="req-1",
        sonarr_series_id=42,
        title="Show - Season 1",
        media_type=MediaType.SERIES,
        season_number=1,
    )


def make_release(
    *,
    files: list[ReleaseFileRecord] | None = None,
    requests: list[ReleaseRequestSnapshot] | None = None,
) -> ReleaseRecord:
    now = datetime.now(UTC)
    return ReleaseRecord(
        id=RELEASE_ID,
        name="Show.S01.1080p.WEB-DL",
        info_hash="OLDHASH",
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
        requests=requests or [],
        torrent_source="RuTracker",
        quality="1080p",
        files=files or [],
        last_exported_info_hash=None,
        export_failures_count=0,
        info_url="https://tracker.example/details/1",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def make_match(
    *,
    magnet_link: str | None = "magnet:?xt=urn:btih:NEWHASH",
    torrent_file_url: str | None = TORRENT_URL,
) -> ReleaseSearchResultRecord:
    return ReleaseSearchResultRecord(
        release_id=RELEASE_ID,
        release_name="Show.S01.1080p.REPACK-GRP",
        size="1 GB",
        magnet_link=magnet_link,
        torrent_file_url=torrent_file_url,
        info_url=None,
        seeders=1,
        leechers=0,
        quality="1080p",
        source="RuTracker",
        request_id="req-1",
    )


class FakeReleaseRepository(UnusedReleaseRepositoryCalls):
    """Records what the re-grab asked of persistence, without a database."""

    def __init__(self, release: ReleaseRecord) -> None:
        self.release = release
        self.files = list(release.files)
        self.updates: dict[str, object] = {}
        self.reconciliations: list[FileReconciliation] = []
        self.mapping_updates: list[list[FileMappingUpdateData]] = []

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        self.updates.update(kwargs)
        return True

    async def sync_release_files(
        self,
        release_id: str,
        reconciliation: FileReconciliation,
    ) -> list[ReleaseFileRecord] | None:
        self.reconciliations.append(reconciliation)
        stored = {file.id: file for file in self.files}
        merged = [
            ReleaseFileRecord(
                id=existing_id,
                name=incoming.name,
                size_bytes=incoming.size_bytes,
                path=incoming.path,
                mapping=stored[existing_id].mapping,
            )
            for existing_id, incoming in reconciliation.matched
        ]
        merged.extend(reconciliation.added)
        self.files = merged
        return merged

    async def update_file_mappings(
        self,
        release_id: str,
        updates: list[FileMappingUpdateData],
    ) -> bool:
        self.mapping_updates.append(list(updates))
        return True


class FakeSearchService:
    is_configured = True

    def __init__(
        self,
        match: ReleaseSearchResultRecord | None,
        *,
        torrent: bytes | None = None,
        fetch_error: Exception | None = None,
    ) -> None:
        self._match = match
        self._torrent = torrent
        self._fetch_error = fetch_error
        self.fetches: list[str] = []

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        results = [self._match] if self._match else []
        return ReleaseSearchResults(results=list(results), query=query, total_results=len(results))

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._match

    async def fetch_torrent(self, url: str) -> bytes:
        self.fetches.append(url)
        if self._fetch_error is not None:
            raise self._fetch_error
        if self._torrent is None:
            raise AssertionError("this test set no torrent file to fetch")
        return self._torrent


class FakeDownloadService(UnusedReleaseDownloadCalls):
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        self.calls.append(release_id)
        return QueuedDownload(
            operation="download",
            status="queued",
            operation_id=None,
            location=None,
            message=None,
            resource_id=release_id,
            details=None,
        )


class FakeWarningRepository(UnusedRequestWarningCalls):
    def __init__(self) -> None:
        self.calls: list[tuple[RequestWarningCode, list[str], list[RequestWarningRecord]]] = []

    async def replace_for_releases(
        self,
        code: RequestWarningCode,
        release_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        self.calls.append((code, list(release_ids), list(warnings)))


class FakeIndexerDirectory(UnusedIndexerDirectoryCalls):
    is_configured = True

    async def list_indexers(self) -> list[IndexerRecord]:
        return []


def rows_for(
    warnings: FakeWarningRepository, code: RequestWarningCode
) -> list[RequestWarningRecord]:
    return next(rows for call_code, _, rows in reversed(warnings.calls) if call_code is code)


def build_regrapper(
    repository: FakeReleaseRepository,
    search_service: FakeSearchService,
    download_service: FakeDownloadService,
    warnings: FakeWarningRepository,
) -> ReleaseRegrapper:
    return ReleaseRegrapper(
        repository=repository,
        search_service=search_service,
        download_service=download_service,
        auto_mapper=ReleaseAutoMapper(
            repository=repository,
            file_matcher=ReleaseFileMatcher(),
            request_repository=stub_media_request_repository(),
        ),
        warning_repository=warnings,
        recompute_state=stub_recompute_state(),
        directory=FakeIndexerDirectory(),
    )


async def test_a_replacement_adds_its_new_files_and_maps_only_those() -> None:
    release = make_release(
        files=[
            stored_file("file-1", f"{ROOT}/Show.S01E01.mkv", episode=1),
            stored_file("file-2", f"{ROOT}/Show.S01E02.mkv", episode=2),
        ],
        requests=[season_request()],
    )
    repository = FakeReleaseRepository(release)
    download_service = FakeDownloadService()
    warnings = FakeWarningRepository()
    search_service = FakeSearchService(
        make_match(),
        torrent=torrent_for("Show.S01E01.mkv", "Show.S01E02.mkv", "Show.S01E03.mkv"),
    )

    regrab = await build_regrapper(repository, search_service, download_service, warnings).regrab(
        release, {}
    )

    assert regrab is True
    assert download_service.calls == [RELEASE_ID]

    reconciliation = repository.reconciliations[0]
    assert reconciliation.missing == []
    assert [record.name for record in reconciliation.added] == [f"{ROOT}/Show.S01E03.mkv"]

    # Only the file the replacement added is written: the two the release already
    # had were mapped once and are not re-derived behind the user's back.
    written = [update.file_id for updates in repository.mapping_updates for update in updates]
    assert written == [reconciliation.added[0].id]
    assert rows_for(warnings, RequestWarningCode.REGRAB_FILES_UNMAPPED) == []


async def test_a_replacement_nobody_can_map_raises_a_warning() -> None:
    release = make_release(
        files=[stored_file("file-1", f"{ROOT}/Show.S01E01.mkv", episode=1)],
        requests=[],
    )
    repository = FakeReleaseRepository(release)
    download_service = FakeDownloadService()
    warnings = FakeWarningRepository()
    search_service = FakeSearchService(
        make_match(), torrent=torrent_for("Show.S01E01.mkv", "Show.S01E02.mkv")
    )

    await build_regrapper(repository, search_service, download_service, warnings).regrab(
        release, {}
    )

    added = repository.reconciliations[0].added
    assert [record.name for record in added] == [f"{ROOT}/Show.S01E02.mkv"]
    assert repository.mapping_updates == []

    rows = rows_for(warnings, RequestWarningCode.REGRAB_FILES_UNMAPPED)
    assert [row.request_id for row in rows] == ["req-1"]
    assert rows[0].release_id == RELEASE_ID
    assert rows[0].details == {"file_ids": [added[0].id], "file_count": 1}


async def test_a_replacement_that_drops_a_stored_file_is_refused() -> None:
    release = make_release(
        files=[
            stored_file("file-1", f"{ROOT}/Show.S01E01.mkv", episode=1),
            stored_file("file-2", f"{ROOT}/Show.S01E02.mkv", episode=2),
        ],
        requests=[season_request()],
    )
    repository = FakeReleaseRepository(release)
    download_service = FakeDownloadService()
    warnings = FakeWarningRepository()
    search_service = FakeSearchService(make_match(), torrent=torrent_for("Show.S01E01.mkv"))

    regrapper = build_regrapper(repository, search_service, download_service, warnings)

    with pytest.raises(ReleaseRegrabRejectedError) as rejected:
        await regrapper.regrab(release, {})

    missing = f"{ROOT}/Show.S01E02.mkv"
    assert rejected.value.missing_files == [missing]
    # Nothing is queued and nothing is rewritten: the release still describes the
    # torrent it actually has.
    assert download_service.calls == []
    assert repository.updates == {}
    assert repository.reconciliations == []

    rows = rows_for(warnings, RequestWarningCode.REGRAB_FILES_MISSING)
    assert [row.request_id for row in rows] == ["req-1"]
    assert rows[0].details == {"missing_files": [missing], "file_count": 1}


async def test_an_unreadable_file_list_leaves_the_stored_files_alone() -> None:
    """A magnet-only result still gets downloaded, it just cannot be reconciled."""

    release = make_release(
        files=[stored_file("file-1", f"{ROOT}/Show.S01E01.mkv", episode=1)],
        requests=[season_request()],
    )
    repository = FakeReleaseRepository(release)
    download_service = FakeDownloadService()
    warnings = FakeWarningRepository()
    search_service = FakeSearchService(make_match(), fetch_error=RuntimeError("torrent 404"))

    regrab = await build_regrapper(repository, search_service, download_service, warnings).regrab(
        release, {}
    )

    assert regrab is True
    assert download_service.calls == [RELEASE_ID]
    assert repository.reconciliations == []
    assert search_service.fetches == [TORRENT_URL]
    touched = {code for code, _, _ in warnings.calls}
    assert RequestWarningCode.REGRAB_FILES_MISSING not in touched
    assert RequestWarningCode.REGRAB_FILES_UNMAPPED not in touched


async def test_a_magnet_only_release_records_every_file_the_torrent_lists() -> None:
    """A grab with no file list is the one case where everything is new."""

    release = make_release(files=[], requests=[season_request()])
    repository = FakeReleaseRepository(release)
    download_service = FakeDownloadService()
    warnings = FakeWarningRepository()
    search_service = FakeSearchService(
        make_match(), torrent=torrent_for("Show.S01E01.mkv", "Show.S01E02.mkv")
    )

    await build_regrapper(repository, search_service, download_service, warnings).regrab(
        release, {}
    )

    added = repository.reconciliations[0].added
    assert [record.name for record in added] == [
        f"{ROOT}/Show.S01E01.mkv",
        f"{ROOT}/Show.S01E02.mkv",
    ]
    assert sorted(
        update.file_id for updates in repository.mapping_updates for update in updates
    ) == sorted(record.id for record in added)
    assert rows_for(warnings, RequestWarningCode.REGRAB_FILES_UNMAPPED) == []


async def test_a_renamed_root_folder_keeps_the_stored_mappings() -> None:
    release = make_release(
        files=[stored_file("file-1", f"{ROOT}/Show.S01E01.mkv", episode=1)],
        requests=[season_request()],
    )
    repository = FakeReleaseRepository(release)
    download_service = FakeDownloadService()
    warnings = FakeWarningRepository()
    search_service = FakeSearchService(
        make_match(), torrent=torrent_for("Show.S01E01.mkv", root=REPACK_ROOT)
    )

    await build_regrapper(repository, search_service, download_service, warnings).regrab(
        release, {}
    )

    reconciliation = repository.reconciliations[0]
    assert reconciliation.added == []
    assert [existing_id for existing_id, _ in reconciliation.matched] == ["file-1"]
    assert repository.files[0].path == f"{REPACK_ROOT}/Show.S01E01.mkv"
    assert repository.files[0].mapping is not None
    assert repository.mapping_updates == []
    assert rows_for(warnings, RequestWarningCode.REGRAB_FILES_MISSING) == []
