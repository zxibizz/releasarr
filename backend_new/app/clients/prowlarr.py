from __future__ import annotations

import httpx
from loguru import logger
from torrentool.api import Torrent

from app.core.config import Settings
from app.schemas.prowlarr import ReleaseData, TorrentFile, TorrentMeta


class ProwlarrClient:
    def __init__(self, settings: Settings) -> None:
        self._enabled = not settings.mock_external_services and bool(
            settings.prowlarr_url and settings.prowlarr_api_key
        )
        self._client: httpx.AsyncClient | None = None
        self._base_url = settings.prowlarr_url
        self._api_key = settings.prowlarr_api_key

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.enabled:
            raise RuntimeError("Prowlarr client is not configured")
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=str(self._base_url),
                headers={"X-Api-Key": str(self._api_key)},
                timeout=30,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(
        self, query: str, indexer_ids: list[int] | None = None
    ) -> list[ReleaseData]:
        if not self.enabled:
            logger.info("Skipping Prowlarr search; client disabled")
            return []
        client = await self._get_client()
        params = [("query", query), ("type", "search")]
        if indexer_ids:
            params.extend(("indexerIds", idx) for idx in indexer_ids)
        response = await client.get("/search", params=params)
        response.raise_for_status()
        return [ReleaseData.model_validate(item) for item in response.json()]

    async def download_torrent(self, download_url: str) -> bytes:
        if not self.enabled:
            raise RuntimeError("Prowlarr client disabled; cannot download torrent")
        client = await self._get_client()
        response = await client.get(download_url)
        response.raise_for_status()
        return response.content

    async def get_torrent(self, download_url: str) -> tuple[TorrentMeta, bytes]:
        raw = await self.download_torrent(download_url)
        torrent = Torrent.from_string(raw)
        meta = TorrentMeta(
            name=torrent.name,
            info_hash=torrent.info_hash,
            total_size=torrent.total_size,
            creation_date=torrent.creation_date,
            files=[TorrentFile(name=f.name, length=f.length) for f in torrent.files],
        )
        return meta, raw
