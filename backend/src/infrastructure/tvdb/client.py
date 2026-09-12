"""HTTP client for TVDB metadata retrieval."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import httpx

from src.application.interfaces.tvdb import TvdbSeriesMetadata, TvdbService, TvdbTranslation
from src.infrastructure.http import build_async_client


class _TvdbAuth(httpx.Auth):
    """HTTPX authentication helper managing TVDB bearer tokens."""

    requires_request_body = True

    def __init__(self, base_url: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._auth_token: str | None = None
        self._lock = asyncio.Lock()
        self.client: httpx.AsyncClient  # attribute populated by httpx

    async def _login(self) -> str:
        response = await self.client.post(
            "/login",
            json={"apiKey": self._api_token},
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        token = data.get("token")
        if not token:
            raise httpx.HTTPError("TVDB authentication response missing token")
        return str(token)

    async def async_auth_flow(self, request: httpx.Request):
        if self._auth_token is None:
            async with self._lock:
                if self._auth_token is None:
                    response: httpx.Response = yield self._build_login_request()
                    response.raise_for_status()
                    await response.aread()
                    payload = response.json()
                    data = payload.get("data") or {}
                    token = data.get("token")
                    if not token:
                        raise httpx.HTTPError("TVDB authentication response missing token")
                    self._auth_token = str(token)

        request.headers["Authorization"] = f"Bearer {self._auth_token}"
        yield request

    def _build_login_request(self) -> httpx.Request:
        return httpx.Request(
            method="POST",
            url=f"{self._base_url}/login",
            json={"apiKey": self._api_token},
        )


class TvdbHttpClient(TvdbService):
    """Fetch series metadata from the TVDB v4 API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = _TvdbAuth(base_url=self._base_url, api_token=api_token)
        self._client = build_async_client(
            base_url=self._base_url,
            auth=self._auth,
            timeout=timeout_seconds,
        )
        self._auth.client = self._client

    async def get_series(
        self,
        tvdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TvdbSeriesMetadata:
        response = await self._client.get(
            f"/series/{tvdb_id}/extended",
            params={"meta": "translations"},
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}

        translations = self._extract_translations(data, languages)
        genres = [str(item) for item in data.get("genres", []) if item]
        image_url = self._safe_str(data.get("image"))

        return TvdbSeriesMetadata(
            tvdb_id=int(data.get("id") or tvdb_id),
            name=self._safe_str(data.get("name")),
            overview=self._safe_str(data.get("overview")),
            image_url=image_url,
            year=self._safe_int(data.get("year")),
            genres=genres,
            translations=translations,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _extract_translations(
        self,
        data: dict[str, object],
        languages: Sequence[str] | None,
    ) -> dict[str, TvdbTranslation]:
        allowed = {language.lower() for language in languages or [] if language}
        translations: dict[str, TvdbTranslation] = {}

        translations_data = data.get("translations")
        if not isinstance(translations_data, dict):
            return translations

        season_number_lookup = self._build_season_number_lookup(data)

        for name_entry in translations_data.get("nameTranslations", []) or []:
            if not isinstance(name_entry, dict):
                continue
            language = self._safe_language(name_entry.get("language"))
            if not language:
                continue
            if allowed and language not in allowed:
                continue
            translation = translations.get(language)
            if translation is None:
                translation = TvdbTranslation(language=language)
                translations[language] = translation
            translation.title = self._safe_str(name_entry.get("name")) or translation.title

        for overview_entry in translations_data.get("overviewTranslations", []) or []:
            if not isinstance(overview_entry, dict):
                continue
            language = self._safe_language(overview_entry.get("language"))
            if not language:
                continue
            if allowed and language not in allowed:
                continue
            translation = translations.get(language)
            if translation is None:
                translation = TvdbTranslation(language=language)
                translations[language] = translation
            translation.overview = (
                self._safe_str(overview_entry.get("overview")) or translation.overview
            )

        for season_entry in translations_data.get("seasonTranslations", []) or []:
            if not isinstance(season_entry, dict):
                continue
            language = self._safe_language(season_entry.get("language"))
            if not language:
                continue
            if allowed and language not in allowed:
                continue
            translation = translations.get(language)
            if translation is None:
                translation = TvdbTranslation(language=language)
                translations[language] = translation
            season_number = self._resolve_season_number(season_entry, season_number_lookup)
            if season_number is None:
                continue
            overview_value = self._safe_str(season_entry.get("overview"))
            if overview_value:
                translation.season_overviews[season_number] = overview_value

        return translations

    def _build_season_number_lookup(self, data: dict[str, object]) -> dict[int, int]:
        lookup: dict[int, int] = {}
        seasons = data.get("seasons")
        if not isinstance(seasons, list):
            return lookup
        for season in seasons:
            if not isinstance(season, dict):
                continue
            season_id_int = self._safe_int(season.get("id"))
            number_int = self._safe_int(season.get("number") or season.get("seasonNumber"))
            if season_id_int is None or number_int is None:
                continue
            lookup[season_id_int] = number_int
        return lookup

    def _resolve_season_number(
        self,
        season_entry: dict[str, object],
        season_number_lookup: dict[int, int],
    ) -> int | None:
        raw_number = self._safe_int(season_entry.get("seasonNumber"))
        if raw_number is not None:
            return raw_number
        season_id = self._safe_int(season_entry.get("seasonId") or season_entry.get("id"))
        if season_id is None:
            return None
        return season_number_lookup.get(season_id)

    def _safe_language(self, value: object) -> str | None:
        if value is None:
            return None
        language = str(value).strip().lower()
        return language or None

    def _safe_int(self, value: object) -> int | None:
        if not isinstance(value, int | float | str):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_str(self, value: object) -> str | None:
        if value is None:
            return None
        result = str(value).strip()
        return result or None


__all__ = ["TvdbHttpClient"]
