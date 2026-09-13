"""The /logs endpoint filters on record.extra.request_id.

User-facing actions therefore have to bind that field, otherwise a request's
activity view stays empty no matter what happened to it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.interfaces.releases import (
    ReleaseFileRecord,
    ReleaseRecord,
    ReleaseSearchResultRecord,
)
from src.application.use_cases.releases.commands import (
    FileMappingCommand,
    QueueReleaseDownloadCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.exceptions import ReleaseDownloadFailedError
from src.application.use_cases.releases.queue_release_download import QueueReleaseDownloadUseCase
from src.application.use_cases.releases.update_file_mappings import (
    UpdateReleaseFileMappingsUseCase,
)
from src.domain.enums import ReleaseStatus


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
        repository=StubReleaseRepository(make_release())  # type: ignore[arg-type]
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
    def __init__(self, candidate: ReleaseSearchResultRecord) -> None:
        self._candidate = candidate

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._candidate if release_id == self._candidate.release_id else None


class FailingDownloadService:
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
    )

    with pytest.raises(ReleaseDownloadFailedError):
        await use_case.execute(QueueReleaseDownloadCommand(request_id="req-1", release_id="rel-1"))

    failures = [record for record in captured_records if record.get("request_id") == "req-1"]
    assert failures, "a failed grab produced no log entry bound to the request"
    assert "client offline" in failures[0]["error"]
