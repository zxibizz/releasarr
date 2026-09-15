"""Tests for the qBittorrent-backed release download service."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from src.domain.enums import ReleaseStatus
from src.infrastructure.qbittorrent.service import QbittorrentReleaseDownloadService


class FakeQbittorrentClient:
    is_configured = True

    def __init__(self, torrent: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.deleted: list[str] = []
        self.torrent = torrent

    async def add_magnet(
        self,
        magnet_link: str,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        paused: bool = False,
    ) -> None:
        self.calls.append(
            (
                "magnet",
                magnet_link,
                save_path,
                category,
                list(tags) if tags is not None else None,
                paused,
            )
        )

    async def add_torrent(
        self,
        torrent_bytes: bytes,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        paused: bool = False,
    ) -> None:
        self.calls.append(
            (
                "torrent",
                torrent_bytes,
                save_path,
                category,
                list(tags) if tags is not None else None,
                paused,
            )
        )

    async def delete_torrent(self, info_hash: str, delete_files: bool = False) -> None:
        self.deleted.append(info_hash)

    async def get_torrent(self, info_hash: str) -> dict[str, Any] | None:
        return self.torrent


@pytest.mark.asyncio
async def test_service_enqueues_magnet() -> None:
    client = FakeQbittorrentClient()
    service = QbittorrentReleaseDownloadService(
        client=client,
        save_path="/downloads",
        category="tv",
        tag_prefix="releasarr",
        paused=False,
    )

    op = await service.queue_download(
        "req-1",
        "rel-1",
        "magnet:?xt=urn:btih:ABC",
    )

    assert client.calls == [
        (
            "magnet",
            "magnet:?xt=urn:btih:ABC",
            "/downloads",
            "tv",
            ["releasarr", "req-1"],
            False,
        )
    ]
    assert op.status == "completed"
    assert op.details is not None
    assert op.details["ingest_source"] == "magnet"
    assert op.details["tags"] == ["releasarr", "req-1"]


@pytest.mark.asyncio
async def test_service_prefers_torrent_bytes() -> None:
    client = FakeQbittorrentClient()
    service = QbittorrentReleaseDownloadService(client=client)

    data = b"binary-data"
    op = await service.queue_download(
        "req-1",
        "rel-1",
        "magnet:?xt=urn:btih:ABC",
        data,
    )

    assert client.calls[0][0] == "torrent"
    assert client.calls[0][1] == data
    assert op.details is not None
    assert op.details["ingest_source"] == "torrent_file"
    assert op.details["torrent_bytes_len"] == len(data)


@pytest.mark.asyncio
async def test_download_directory_comes_from_the_torrent() -> None:
    """qBittorrent knows the real location; the configured path is only a guess."""

    client = FakeQbittorrentClient(torrent={"save_path": "/media/tv-downloads"})
    service = QbittorrentReleaseDownloadService(client=client, save_path="/downloads")

    assert await service.get_download_directory("ABC") == "/media/tv-downloads"


@pytest.mark.asyncio
async def test_download_directory_falls_back_to_the_configured_path() -> None:
    client = FakeQbittorrentClient(torrent=None)
    service = QbittorrentReleaseDownloadService(client=client, save_path="/downloads")

    assert await service.get_download_directory("ABC") == "/downloads"


@pytest.mark.asyncio
async def test_torrent_state_is_projected_onto_the_release() -> None:
    client = FakeQbittorrentClient(
        torrent={
            "state": "downloading",
            "progress": 0.42,
            "dlspeed": 2048,
            "upspeed": 0,
            "num_seeds": 3,
            "num_leechs": 1,
            "ratio": 0.1,
            "total_size": 4096,
        }
    )
    service = QbittorrentReleaseDownloadService(client=client)

    state = await service.get_torrent_state("abc123")

    assert state is not None
    assert state.progress == 42.0
    assert state.download_speed == 2048
    assert state.seeders == 3
    assert state.size_bytes == 4096
    assert state.status is ReleaseStatus.DOWNLOADING
    assert state.completed_at is None


@pytest.mark.asyncio
async def test_torrent_state_is_none_for_a_torrent_the_client_lacks() -> None:
    service = QbittorrentReleaseDownloadService(client=FakeQbittorrentClient(torrent=None))

    assert await service.get_torrent_state("abc123") is None
