"""Tests for the qBittorrent client's category lookup."""

from __future__ import annotations

import httpx
import pytest

from src.infrastructure.http import HttpClientError
from src.infrastructure.qbittorrent import QbittorrentClient


def _client(handler: httpx.MockTransport) -> QbittorrentClient:
    return QbittorrentClient(
        base_url="https://qb.example/api/v2",
        username="admin",
        password="secret",
        _transport=handler,
    )


@pytest.mark.asyncio
async def test_list_categories_returns_the_names_sorted() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, text="Ok.")
        assert request.url.path.endswith("/torrents/categories")
        return httpx.Response(
            200,
            json={
                "tv": {"name": "tv", "savePath": "/tv"},
                "releasarr": {"name": "releasarr", "savePath": "/downloads"},
            },
        )

    assert await _client(httpx.MockTransport(handler)).list_categories() == ["releasarr", "tv"]


@pytest.mark.asyncio
async def test_list_categories_reauthenticates_once_on_a_stale_session() -> None:
    logins = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal logins
        if request.url.path.endswith("/auth/login"):
            logins += 1
            return httpx.Response(200, text="Ok.")
        if logins < 2:
            return httpx.Response(403)
        return httpx.Response(200, json={"tv": {"name": "tv"}})

    assert await _client(httpx.MockTransport(handler)).list_categories() == ["tv"]
    assert logins == 2


@pytest.mark.asyncio
async def test_list_categories_raises_rather_than_reporting_an_empty_client() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, text="Ok.")
        return httpx.Response(500, text="boom")

    with pytest.raises(HttpClientError):
        await _client(httpx.MockTransport(handler)).list_categories()
