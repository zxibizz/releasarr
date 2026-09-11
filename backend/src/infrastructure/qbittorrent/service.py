"""Release download service backed by qBittorrent."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from src.application.interfaces.releases import QueuedDownload, ReleaseDownloadService


class QbittorrentClientPort(Protocol):
    """Subset of the qBittorrent client used by the download service."""

    async def add_magnet(
        self,
        magnet_link: str,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        paused: bool = False,
    ) -> None: ...

    async def add_torrent(
        self,
        torrent_bytes: bytes,
        *,
        save_path: str | None = None,
        category: str | None = None,
        tags: Sequence[str] | None = None,
        paused: bool = False,
    ) -> None: ...

    async def delete_torrent(self, info_hash: str, delete_files: bool = False) -> None: ...


@dataclass(slots=True)
class QbittorrentReleaseDownloadService(ReleaseDownloadService):
    """Release download service that enqueues torrents via qBittorrent."""

    client: QbittorrentClientPort
    save_path: str | None = None
    category: str | None = None
    tag_prefix: str | None = None
    paused: bool = False

    async def queue_download(
        self,
        request_id: str,
        release_id: str,
        magnet_link: str,
        torrent_bytes: bytes | None = None,
    ) -> QueuedDownload:
        tags = self._build_tags(request_id)
        try:
            if torrent_bytes is not None:
                await self.client.add_torrent(
                    torrent_bytes,
                    save_path=self.save_path,
                    category=self.category,
                    tags=tags,
                    paused=self.paused,
                )
                ingest_source = "torrent_file"
            else:
                await self.client.add_magnet(
                    magnet_link,
                    save_path=self.save_path,
                    category=self.category,
                    tags=tags,
                    paused=self.paused,
                )
                ingest_source = "magnet"
        except Exception as exc:  # pragma: no cover - network errors wrapped upstream
            raise RuntimeError(str(exc)) from exc

        details: dict[str, object] = {
            "request_id": request_id,
            "release_id": release_id,
            "ingest_source": ingest_source,
            "magnet_link": magnet_link,
        }
        if tags:
            details["tags"] = tags
        if torrent_bytes is not None:
            details["torrent_bytes_len"] = len(torrent_bytes)

        return QueuedDownload(
            operation="queue_download",
            status="completed",
            operation_id=None,
            location=None,
            message=None,
            resource_id=release_id,
            details=details,
        )

    def _build_tags(self, request_id: str) -> list[str]:
        tags: list[str] = []
        if self.tag_prefix:
            tags.append(self.tag_prefix)
        tags.append(request_id)
        return tags

    async def delete_download(self, release_id: str) -> None:
        await self.client.delete_torrent(release_id, delete_files=True)


__all__ = ["QbittorrentReleaseDownloadService"]
