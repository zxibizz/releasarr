"""The /logs endpoint filters on record.extra.request_id.

User-facing actions therefore have to bind that field, otherwise a request's
activity view stays empty no matter what happened to it.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from loguru import logger

from src.application.interfaces.releases import ReleaseFileRecord, ReleaseRecord
from src.application.use_cases.releases.commands import (
    FileMappingCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.update_file_mappings import (
    UpdateReleaseFileMappingsUseCase,
)
from src.domain.enums import ReleaseStatus


@pytest.fixture()
def captured_records() -> Iterator[list[dict[str, Any]]]:
    """Collect the ``extra`` payload Loguru would serialise to the log file."""

    records: list[dict[str, Any]] = []
    sink_id = logger.add(
        lambda message: records.append(
            {
                "message": message.record["message"],
                **message.record["extra"],
            }
        ),
        level="INFO",
    )
    try:
        yield records
    finally:
        logger.remove(sink_id)


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
