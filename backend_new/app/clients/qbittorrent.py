from __future__ import annotations

import httpx
from loguru import logger

from app.core.config import Settings


class QBittorrentClient:
    def __init__(self, settings: Settings) -> None:
        self._enabled = (
            not settings.mock_external_services
            and bool(settings.qbittorrent_url and settings.qbittorrent_username)
        )
        self._base_url = settings.qbittorrent_url
        self._username = settings.qbittorrent_username
        self._password = settings.qbittorrent_password
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.enabled:
            raise RuntimeError("qBittorrent client is not configured")
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=str(self._base_url), timeout=30)
            await self._authenticate()
        return self._client

    async def _authenticate(self) -> None:
        if not self._client:
            return
        logger.debug("Authenticating against qBittorrent")
        response = await self._client.post(
            "/api/v2/auth/login",
            data={"username": self._username, "password": self._password},
        )
        response.raise_for_status()
        if response.text != "Ok.":
            raise RuntimeError("Failed to authenticate with qBittorrent")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def add_torrent(self, torrent_data: bytes, save_path: str | None = None) -> None:
        if not self.enabled:
            logger.debug("Skipping qBittorrent add_torrent; client disabled")
            return
        client = await self._get_client()
        files = {"torrents": ("download.torrent", torrent_data, "application/x-bittorrent")}
        data = {"autoTMM": "false"}
        if save_path:
            data["savepath"] = save_path
        response = await client.post("/api/v2/torrents/add", data=data, files=files)
        response.raise_for_status()
