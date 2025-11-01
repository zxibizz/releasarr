from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx
from loguru import logger

from app.core.config import Settings


class SonarrClient:
    """Thin async wrapper around the Sonarr API used for series orchestration."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = (
            not settings.mock_external_services
            and bool(settings.sonarr_url and settings.sonarr_api_key)
        )
        self._base_url = settings.sonarr_url
        self._api_key = settings.sonarr_api_key
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.enabled:
            raise RuntimeError("Sonarr client is not configured")
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=str(self._base_url),
                headers={"X-Api-Key": str(self._api_key)},
                timeout=60,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ensure_series(
        self,
        tvdb_id: int,
        title: str,
        quality_profile_id: int = 1,
        language_profile_id: int = 1,
        root_folder_path: str = "/data/series",
    ) -> dict[str, Any] | None:
        """
        Creates the series in Sonarr if it does not exist yet.
        Returns the Sonarr series payload or ``None`` when client is disabled.
        """

        if not self.enabled:
            logger.debug("Skipping Sonarr ensure_series; client disabled")
            return None

        client = await self._get_client()
        logger.info("Ensuring Sonarr has series for %s", title)
        payload = {
            "tvdbId": tvdb_id,
            "title": title,
            "qualityProfileId": quality_profile_id,
            "languageProfileId": language_profile_id,
            "rootFolderPath": root_folder_path,
            "seasonFolder": True,
            "monitored": True,
            "tags": [],
            "addOptions": {
                "monitor": "all",
                "searchForMissingEpisodes": False,
            },
        }
        response = await client.post("/api/v3/series", json=payload)
        if response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED):
            return response.json()

        if response.status_code == HTTPStatus.CONFLICT:
            # Already exists, fetch current state
            logger.debug("Series already exists in Sonarr, fetching current metadata")
            lookup = await client.get("/api/v3/series", params={"tvdbId": tvdb_id})
            lookup.raise_for_status()
            data = lookup.json()
            if isinstance(data, list) and data:
                return data[0]
            return None

        logger.warning(
            "Sonarr ensure_series failed with status %s: %s",
            response.status_code,
            response.text,
        )
        response.raise_for_status()
        return None
