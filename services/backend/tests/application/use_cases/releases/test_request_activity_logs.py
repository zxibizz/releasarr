"""The /logs endpoint filters on record.extra.request_id.

User-facing actions therefore have to bind that field, otherwise a request's
activity view stays empty no matter what happened to it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.interfaces.indexers import IndexerRecord
from src.application.interfaces.releases import (
    QueuedDownload,
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
)
from src.application.use_cases.releases.commands import (
    FileMappingCommand,
    QueueReleaseDownloadCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.exceptions import ReleaseDownloadFailedError
from src.application.use_cases.releases.queue_release_download import QueueReleaseDownloadUseCase
from src.application.use_cases.releases.regrab import ReleaseRegrapper
from src.application.use_cases.releases.update_file_mappings import (
    UpdateReleaseFileMappingsUseCase,
)
from src.domain.enums import ReleaseStatus
from tests.builders import (
    stub_auto_mapper,
    stub_enqueue_sync,
    stub_existing_release_replacer,
    stub_recompute_state,
    stub_warning_repository,
)
from tests.fakes import (
    UnusedIndexerDirectoryCalls,
    UnusedReleaseDownloadCalls,
    UnusedReleaseRepositoryCalls,
)


class StubReleaseRepository:
    def __init__(self, release: ReleaseRecord) -> None:
        self._release = release

    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        return self._release if release_id == self._release.id else None

    async def update_file_mappings(self, release_id: str, updates: Any) -> bool:
        return True

    async def update_release(self, release_id: str, **kwargs: Any) -> bool:
        return True


def make_release() -> ReleaseRecord:
    return ReleaseRecord(
        id="rel-1",
        name="Example.S01E01",
        info_hash="ABC123",
        size_bytes=1024,
        status=ReleaseStatus.DOWNLOADING,
        progress=10.0,
        download_speed=0.0,
        upload_speed=0.0,
        seeders=1,
        leechers=0,
        ratio=0.0,
        added_at=datetime.now(UTC),
        completed_at=None,
        torrent_source=None,
        quality=None,
        request_ids=["req-1"],
        requests=[],
        last_exported_info_hash=None,
        export_failures_count=0,
        files=[
            ReleaseFileRecord(
                id="file-1",
                name="Example.S01E01.mkv",
                size_bytes=1024,
                path="Example.S01E01.mkv",
                mapping=None,
            )
        ],
    )


async def test_saving_a_file_mapping_logs_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    use_case = UpdateReleaseFileMappingsUseCase(
        repository=StubReleaseRepository(make_release()),  # type: ignore[arg-type]
        warning_repository=stub_warning_repository(),
        enqueue_sync=stub_enqueue_sync(),
        recompute_state=stub_recompute_state(),
    )
    command = UpdateFileMappingsCommand(
        release_id="rel-1",
        files=[
            FileMappingCommand(
                file_id="file-1",
                mapping_type="series",
                request_id="req-1",
                request_title="Example - Season 1",
                season=1,
                episode=1,
            )
        ],
    )

    await use_case.execute(command)

    mapped = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert mapped, "file mapping produced no log entry bound to the request"
    assert mapped[0]["release_id"] == "rel-1"


class StubEmptyReleaseRepository:
    async def get_release(self, release_id: str) -> ReleaseRecord | None:
        return None


class StubSearchService:
    is_configured = True

    def __init__(self, candidate: ReleaseSearchResultRecord) -> None:
        self._candidate = candidate

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._candidate if release_id == self._candidate.release_id else None


class FailingDownloadService:
    is_configured = True

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> Any:
        raise RuntimeError("client offline")


async def test_a_failed_grab_logs_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    candidate = ReleaseSearchResultRecord(
        release_id="rel-1",
        release_name="Example.S01E01",
        size="1 GB",
        magnet_link="magnet:?xt=urn:btih:ABC123",
        torrent_file_url=None,
        info_url=None,
        seeders=10,
        leechers=2,
        quality="1080p",
        source="indexer",
        request_id="req-1",
    )
    use_case = QueueReleaseDownloadUseCase(
        repository=StubEmptyReleaseRepository(),  # type: ignore[arg-type]
        download_service=FailingDownloadService(),  # type: ignore[arg-type]
        search_service=StubSearchService(candidate),  # type: ignore[arg-type]
        auto_mapper=stub_auto_mapper(),
        existing_release_replacer=stub_existing_release_replacer(),
        recompute_state=stub_recompute_state(),
    )

    with pytest.raises(ReleaseDownloadFailedError):
        await use_case.execute(QueueReleaseDownloadCommand(request_id="req-1", release_id="rel-1"))

    failures = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert failures, "a failed grab produced no log entry bound to the request"
    assert "client offline" in failures[0]["error"]


class CheckRepository(UnusedReleaseRepositoryCalls):
    """The one repository call a re-grab check makes."""

    def __init__(self) -> None:
        self.updates: dict[str, object] = {}

    async def update_release(self, release_id: str, **kwargs: object) -> bool:
        self.updates.update(kwargs)
        return True


class CheckSearchService:
    is_configured = True

    def __init__(self, results: list[ReleaseSearchResultRecord]) -> None:
        self._results = results

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        return ReleaseSearchResults(
            results=list(self._results), query=query, total_results=len(self._results)
        )

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        """A re-grab check searches; it never reads back a cached candidate."""

        return None

    async def fetch_torrent(self, url: str) -> bytes:
        raise AssertionError("every result here carries a magnet, not a torrent file")


class CheckDownloadService(UnusedReleaseDownloadCalls):
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


class CheckIndexerDirectory(UnusedIndexerDirectoryCalls):
    is_configured = True

    async def list_indexers(self) -> list[IndexerRecord]:
        return []


def make_checkable_release(
    *, info_hash: str = "ABC123", request_ids: list[str] | None = None
) -> ReleaseRecord:
    """`make_release` as the re-grab check sees it: from an indexer, for a request."""

    return replace(
        make_release(),
        info_hash=info_hash,
        torrent_source="RuTracker",
        request_ids=request_ids if request_ids is not None else ["req-1"],
    )


def make_indexer_result(release: ReleaseRecord, *, info_hash: str) -> ReleaseSearchResultRecord:
    return ReleaseSearchResultRecord(
        release_id=release.id,
        release_name=release.name,
        size="1 GB",
        magnet_link=f"magnet:?xt=urn:btih:{info_hash}",
        torrent_file_url=None,
        info_url=None,
        seeders=1,
        leechers=0,
        quality="1080p",
        source="RuTracker",
        request_id="req-1",
    )


def build_regrapper(search_service: CheckSearchService) -> ReleaseRegrapper:
    return ReleaseRegrapper(
        repository=CheckRepository(),
        search_service=search_service,
        download_service=CheckDownloadService(),
        auto_mapper=stub_auto_mapper(),
        warning_repository=stub_warning_repository(),
        recompute_state=stub_recompute_state(),
        directory=CheckIndexerDirectory(),
    )


async def test_a_check_that_finds_no_change_logs_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    """The hourly sweep's usual answer has to reach the request it looked at."""

    release = make_checkable_release()
    regrapper = build_regrapper(
        CheckSearchService([make_indexer_result(release, info_hash=release.info_hash)])
    )

    assert await regrapper.regrab(release, {}) is False

    records = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert records, "an unchanged release produced no log entry bound to the request"
    assert records[0]["release_id"] == release.id
    assert records[0]["info_hash"] == release.info_hash


async def test_a_check_logs_once_per_request_holding_the_release(
    captured_records: list[dict[str, Any]],
) -> None:
    """One release, several requests: each of them filters the log by its own id."""

    release = make_checkable_release(request_ids=["req-1", "req-2"])
    regrapper = build_regrapper(
        CheckSearchService([make_indexer_result(release, info_hash=release.info_hash)])
    )

    await regrapper.regrab(release, {})

    for request_id in ("req-1", "req-2"):
        assert [record for record in captured_records if record.get("request_id") == request_id]


async def test_a_check_the_indexer_no_longer_answers_for_logs_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    release = replace(make_checkable_release(), search_query="Show S01")
    regrapper = build_regrapper(CheckSearchService([]))

    assert await regrapper.regrab(release, {}) is False

    records = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert records, "a release missing from its indexer's results logged nothing"
    assert records[0]["release_id"] == release.id
    # What was searched is what makes a miss diagnosable.
    assert records[0]["query"] == "Show S01"
    assert records[0]["results"] == 0


async def test_a_successful_regrab_logs_against_the_request(
    captured_records: list[dict[str, Any]],
) -> None:
    release = make_checkable_release()
    regrapper = build_regrapper(
        CheckSearchService([make_indexer_result(release, info_hash="NEWHASH")])
    )

    assert await regrapper.regrab(release, {}) is True

    records = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert records, "a re-grab produced no log entry bound to the request"
    assert records[0]["old_hash"] == release.info_hash
    assert records[0]["new_hash"] == "NEWHASH"
