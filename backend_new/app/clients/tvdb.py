from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.core.config import Settings


class TvdbClient:
    def __init__(self, settings: Settings) -> None:
        self._enabled = not settings.mock_external_services and bool(settings.tvdb_api_key)
        self._base_url = settings.tvdb_url or "https://api4.thetvdb.com/v4"
        self._api_key = settings.tvdb_api_key
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.enabled:
            raise RuntimeError("TVDB client is not configured")
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30)
        if self._token is None:
            await self._authenticate()
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self._token = None

    async def _authenticate(self) -> None:
        if not self.enabled:
            return
        if not self._client:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30)
        logger.debug("Requesting TVDB auth token")
        response = await self._client.post("/login", json={"apiKey": self._api_key})
        response.raise_for_status()
        self._token = response.json()["data"]["token"]
        self._client.headers["Authorization"] = f"Bearer {self._token}"

    async def get_series(self, tvdb_id: int) -> dict[str, Any] | None:
        if not self.enabled:
            logger.debug("Skipping TVDB get_series; client disabled")
            return None
        client = await self._get_client()
        response = await client.get(
            f"/series/{tvdb_id}/extended",
            params={"meta": "translations"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("data")
