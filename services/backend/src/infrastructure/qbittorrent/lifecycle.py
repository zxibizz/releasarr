"""Release lifecycle service backed by qBittorrent."""

from __future__ import annotations

from dataclasses import dataclass

from src.application.interfaces.releases import ReleaseLifecycleService

from .client import QbittorrentClient


@dataclass(slots=True)
class QbittorrentReleaseLifecycleService(ReleaseLifecycleService):
    """Lifecycle service that pauses/resumes torrents via qBittorrent.
    
    This service uses the torrent's info hash to identify and control
    downloads in the qBittorrent client.
    """

    client: QbittorrentClient

    async def pause(self, release_id: str) -> bool:
        """Pause a release download by its info hash.
        
        The release_id is expected to be the torrent's info hash.
        Returns True if the pause command was successful.
        """
        return await self.client.pause_torrent(release_id)

    async def resume(self, release_id: str) -> bool:
        """Resume a paused release download by its info hash.
        
        The release_id is expected to be the torrent's info hash.
        Returns True if the resume command was successful.
        """
        return await self.client.resume_torrent(release_id)


__all__ = ["QbittorrentReleaseLifecycleService"]
