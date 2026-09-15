"""Tests for the Prowlarr-backed release search service."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from src.application.interfaces.releases import ReleaseSearchResults, ReleaseSearchUnavailableError
from src.infrastructure.prowlarr import ProwlarrReleaseSearchService


@pytest.mark.asyncio
async def test_search_returns_mapped_results() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/search")
        assert request.headers["X-Api-Key"] == "token"
        payload = [
            {
                "title": "Example Release",
                "guid": "abc123",
                "size": 1048576,
                "magnetUrl": "magnet:?xt=urn:btih:ABC",
                "downloadUrl": "https://prowlarr/download/1",
                "infoUrl": "https://tracker/info/1",
                "seeders": 10,
                "leechers": 2,
                "quality": "1080p",
                "indexer": "IndexerOne",
                "publishDate": "2026-03-04T12:30:00Z",
            },
            {
                "title": "Second Release",
                "guid": "def456",
                "size": 512,
                "downloadUrl": "https://prowlarr/download/2",
                "seeders": 5,
                "leechers": 1,
                "quality": "720p",
                "indexer": "IndexerTwo",
            },
        ]
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    results = await service.search("Example", request_id="req-1")

    assert isinstance(results, ReleaseSearchResults)
    assert results.query == "Example"
    assert results.total_results == 2

    first = results.results[0]
    assert first.release_id == "abc123"
    assert first.release_name == "Example Release"
    assert first.size == "1.00 MB"
    assert first.magnet_link == "magnet:?xt=urn:btih:ABC"
    assert first.torrent_file_url == "https://prowlarr/download/1"
    assert first.info_url == "https://tracker/info/1"
    assert first.seeders == 10
    assert first.leechers == 2
    assert first.quality == "1080p"
    assert first.source == "IndexerOne"
    assert first.request_id == "req-1"
    assert first.publish_date == datetime(2026, 3, 4, 12, 30, tzinfo=UTC)

    # Prowlarr omits publishDate for some indexers; the field stays optional.
    assert results.results[1].publish_date is None


@pytest.mark.asyncio
async def test_search_handles_unavailable_indexers() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = {"message": "Search failed due to all selected indexers being unavailable"}
        return httpx.Response(400, json=payload)

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    results = await service.search("Anything")

    assert results.total_results == 0
    assert results.results == []


@pytest.mark.asyncio
async def test_search_skips_results_without_links() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = [
            {"title": "Missing Links", "guid": "no-links"},
            {
                "title": "Magnet Only",
                "guid": "magnet",
                "magnetUrl": "magnet:?xt=urn:btih:MAG",
                "size": 1024,
            },
        ]
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    results = await service.search("Test")

    assert results.total_results == 1
    assert results.results[0].release_id == "magnet"
    assert results.results[0].magnet_link == "magnet:?xt=urn:btih:MAG"
    assert results.results[0].torrent_file_url is None


@pytest.mark.asyncio
async def test_search_sends_indexer_ids_param_when_scoped() -> None:
    seen_params: list[tuple[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_params.extend(request.url.params.multi_items())
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    await service.search("Example", indexer_id=42)

    assert ("indexerIds", "42") in seen_params


@pytest.mark.asyncio
async def test_search_does_not_retry_transport_errors() -> None:
    """A per-indexer search owns its own retry budget, not the client's."""

    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    with pytest.raises(ReleaseSearchUnavailableError):
        await service.search("Example", indexer_id=1)

    assert attempts == 1


@pytest.mark.asyncio
async def test_search_scoped_to_indexer_treats_all_unavailable_as_failure() -> None:
    """Scoped to one indexer, 'all selected indexers' means that indexer is down."""

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = {"message": "Search failed due to all selected indexers being unavailable"}
        return httpx.Response(400, json=payload)

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    with pytest.raises(ReleaseSearchUnavailableError):
        await service.search("Anything", indexer_id=7)


@pytest.mark.asyncio
async def test_search_wraps_non_400_http_errors() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "boom"})

    transport = httpx.MockTransport(handler)
    service = ProwlarrReleaseSearchService(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=transport,
    )

    with pytest.raises(ReleaseSearchUnavailableError):
        await service.search("Anything", indexer_id=1)
