"""Tests for in-memory release service adapters."""

from __future__ import annotations

import pytest

from src.application.interfaces.releases import ReleaseSearchResultRecord, ReleaseSearchResults
from src.infrastructure.releases.services import (
    InMemoryReleaseDownloadService,
    InMemoryReleaseLifecycleService,
    InMemoryReleaseSearchService,
)


@pytest.mark.asyncio
async def test_lifecycle_service_tracks_paused_state() -> None:
    service = InMemoryReleaseLifecycleService()

    assert await service.pause("rel-1") is True
    assert await service.pause("rel-1") is False
    assert await service.resume("rel-1") is True
    assert await service.resume("rel-1") is False


@pytest.mark.asyncio
async def test_search_service_returns_registered_results() -> None:
    service = InMemoryReleaseSearchService()
    record = ReleaseSearchResultRecord(
        release_id="rel-1",
        release_name="Example",
        size="1 GB",
        magnet_link="magnet:?xt=urn:btih:ABC",
        torrent_file_url=None,
        info_url=None,
        seeders=10,
        leechers=2,
        quality="1080p",
        source="stub",
        request_id="req-1",
    )
    service.register_results("query", request_id="req-1", results=[record])
    service.register_torrent("rel-1", b"torrent-bytes")

    results = await service.search("query", request_id="req-1")
    assert isinstance(results, ReleaseSearchResults)
    assert results.total_results == 1
    assert results.results[0].release_id == "rel-1"
    assert service.resolve("rel-1") is record
    assert await service.fetch_torrent("memory://rel-1") == b"torrent-bytes"


@pytest.mark.asyncio
async def test_download_service_records_queue_requests() -> None:
    service = InMemoryReleaseDownloadService()

    op = await service.queue_download("req-1", "rel-1")

    assert service.queued == [("req-1", "rel-1")]
    assert op.operation == "queue_download"
    assert op.status == "accepted"
    assert op.details == {"request_id": "req-1", "release_id": "rel-1"}
