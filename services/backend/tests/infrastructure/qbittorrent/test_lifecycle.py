"""Tests for qBittorrent lifecycle service."""

from __future__ import annotations

import pytest
from httpx import AsyncBaseTransport, Request, Response

from src.infrastructure.qbittorrent import QbittorrentClient, QbittorrentReleaseLifecycleService


class FakeTransport(AsyncBaseTransport):
    """Mock transport that records requests and returns predefined responses."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.responses: dict[str, Response] = {}

    def set_response(self, path: str, status_code: int) -> None:
        self.responses[path] = Response(status_code)

    async def handle_async_request(self, request: Request) -> Response:
        path = request.url.path.removeprefix("/api/v2")
        method = request.method
        self.requests.append((method, path, dict(request.url.params)))

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


def _paths(transport: FakeTransport) -> list[str]:
    return [req[1] for req in transport.requests if req[1] != "/auth/login"]


@pytest.mark.asyncio
async def test_pause_uses_the_qbittorrent_5_endpoint(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    result = await lifecycle_service.pause("ABCDEF123456")

    assert result is True
    assert _paths(transport) == ["/torrents/stop"]


@pytest.mark.asyncio
async def test_resume_uses_the_qbittorrent_5_endpoint(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    result = await lifecycle_service.resume("ABCDEF123456")

    assert result is True
    assert _paths(transport) == ["/torrents/start"]


@pytest.mark.asyncio
async def test_pause_falls_back_to_the_qbittorrent_4_endpoint(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/stop", 404)

    result = await lifecycle_service.pause("ABCDEF123456")

    assert result is True
    assert _paths(transport) == ["/torrents/stop", "/torrents/pause"]


@pytest.mark.asyncio
async def test_resume_falls_back_to_the_qbittorrent_4_endpoint(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/start", 404)

    result = await lifecycle_service.resume("ABCDEF123456")

    assert result is True
    assert _paths(transport) == ["/torrents/start", "/torrents/resume"]


@pytest.mark.asyncio
async def test_pause_does_not_retry_the_old_name_on_a_real_failure(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/stop", 500)

    result = await lifecycle_service.pause("ABCDEF123456")

    assert result is False
    assert _paths(transport) == ["/torrents/stop"]


@pytest.mark.asyncio
async def test_resume_returns_false_on_failure(
    lifecycle_service: QbittorrentReleaseLifecycleService,
    transport: FakeTransport,
) -> None:
    transport.set_response("/torrents/start", 404)
    transport.set_response("/torrents/resume", 500)

    result = await lifecycle_service.resume("ABCDEF123456")

    assert result is False
