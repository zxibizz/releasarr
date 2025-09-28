"""Tests for the qBittorrent-backed release download service."""

from __future__ import annotations

import pytest

from src.infrastructure.qbittorrent.service import QbittorrentReleaseDownloadService


class FakeQbittorrentClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def add_magnet(
        self,
        magnet_link: str,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        paused: bool = False,
    ) -> None:
        self.calls.append(
            (
                "magnet",
                magnet_link,
                save_path,
                category,
                tags,
                paused,
            )
        )

    async def add_torrent(
        self,
        torrent_bytes: bytes,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        paused: bool = False,
    ) -> None:
        self.calls.append(
            (
                "torrent",
                torrent_bytes,
                save_path,
                category,
                tags,
                paused,
            )
        )


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
    assert op.details["ingest_source"] == "torrent_file"
    assert op.details["torrent_bytes_len"] == len(data)
