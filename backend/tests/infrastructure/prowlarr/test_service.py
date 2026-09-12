"""Tests for the Prowlarr-backed release search service."""

from __future__ import annotations

import httpx
import pytest

from src.application.interfaces.releases import ReleaseSearchResults
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
