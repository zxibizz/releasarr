from __future__ import annotations

import httpx
from loguru import logger

from app.core.config import Settings
from app.schemas.tvdb import TvdbShowData


class TvdbClient:
    def __init__(self, settings: Settings) -> None:
        self._enabled = not settings.mock_external_services and bool(
            settings.tvdb_api_key
        )
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
        logger.info("Requesting TVDB auth token")
        response = await self._client.post("/login", json={"apiKey": self._api_key})
        response.raise_for_status()
        self._token = response.json()["data"]["token"]
        self._client.headers["Authorization"] = f"Bearer {self._token}"

    async def get_series(self, tvdb_id: int) -> TvdbShowData | None:
        if not self.enabled:
            logger.info("Skipping TVDB get_series; client disabled")
            return None
        client = await self._get_client()
        response = await client.get(
            f"/series/{tvdb_id}/extended",
            params={"meta": "translations"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json().get("data") or {}
        name = data.get("name")
        translations: dict[str, str] = {}
        for t in data.get("translations", {}).get("nameTranslations", []) or []:
            lang = t.get("language")
            translated_name = t.get("name")
            if lang and translated_name:
                translations[lang] = translated_name

        overview_translations: dict[str, str] = {}
        for t in data.get("translations", {}).get("overviewTranslations", []) or []:
            lang = t.get("language")
            overview_text = t.get("overview")
            if lang and overview_text:
                overview_translations[lang] = overview_text

        genres: list[str] = []
        for genre in data.get("genres") or []:
            if isinstance(genre, dict):
                name = genre.get("name")
                if name:
                    genres.append(name)
            elif isinstance(genre, str):
                genres.append(genre)

        return TvdbShowData(
            id=data.get("id"),
            year=data.get("year"),
            genres=genres,
            country=data.get("originalCountry"),
            title=translations.get("rus") or translations.get("eng") or name,
            title_en=translations.get("eng"),
            image_url=data.get("image"),
            overview=overview_translations.get("rus")
            or overview_translations.get("eng")
            or data.get("overview"),
        )
