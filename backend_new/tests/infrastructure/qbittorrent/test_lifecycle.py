"""Tests for qBittorrent lifecycle service."""

from __future__ import annotations

import pytest
from httpx import Response

from src.infrastructure.qbittorrent import QbittorrentClient, QbittorrentReleaseLifecycleService


class FakeTransport:
    """Mock transport that records requests and returns predefined responses."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict]] = []
        self.responses: dict[str, Response] = {}

    def set_response(self, path: str, status_code: int) -> None:
        self.responses[path] = Response(status_code)

    async def handle_async_request(self, request):
        path = request.url.path
        method = request.method
        self.requests.append((method, path, dict(request.url.params)))
        
        # Default auth success
        if path == "/auth/login":
            return Response(200)
        
        return self.responses.get(path, Response(200))


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def client(transport: FakeTransport) -> QbittorrentClient:
    return QbittorrentClient(
        base_url="http://qbt.test:8080",
        username="admin",
        password="secret",
        _transport=transport,
    )


@pytest.fixture
def lifecycle_service(client: QbittorrentClient) -> QbittorrentReleaseLifecycleService:
    return QbittorrentReleaseLifecycleService(client=client)


@pytest.mark.asyncio
async def test_pause_calls_qbittorrent_api(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/pause", 200)

    result = await lifecycle_service.pause("ABCDEF123456")

    assert result is True
    # Should have login + pause requests
    assert any(req[1] == "/torrents/pause" for req in transport.requests)


@pytest.mark.asyncio
async def test_resume_calls_qbittorrent_api(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/resume", 200)

    result = await lifecycle_service.resume("ABCDEF123456")

    assert result is True
    assert any(req[1] == "/torrents/resume" for req in transport.requests)


@pytest.mark.asyncio
async def test_pause_returns_false_on_failure(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/pause", 500)

    result = await lifecycle_service.pause("ABCDEF123456")

    assert result is False


@pytest.mark.asyncio
async def test_resume_returns_false_on_failure(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/resume", 500)

    result = await lifecycle_service.resume("ABCDEF123456")

    assert result is False
