"""HTTP client for TMDB metadata retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from src.application.interfaces.tmdb import (
    TmdbMovieMetadata,
    TmdbSearchResult,
    TmdbService,
    TmdbTranslation,
)
from src.application.utility.languages import TWO_TO_THREE_LETTER, to_two_letter
from src.infrastructure.http import BaseHttpClient

# TMDB serves posters from a separate image host and reports only the path.
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


class TmdbHttpClient(TmdbService):
    """Fetch movie metadata from the TMDB v3 API."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # TMDB hands out a v3 key and a v4 read access token; the latter is a JWT
        # and goes in the Authorization header, the former in the query string.
        # Accepting both saves callers from having to know which one they copied.
        self._api_token = api_token
        headers: dict[str, str] = {}
        self._auth_params: dict[str, str] = {}
        if "." in api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        elif api_token:
            self._auth_params["api_key"] = api_token

        self._http = BaseHttpClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout_seconds,
            transport=transport,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._api_token)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get_movie(
        self,
        tmdb_id: int,
        languages: Sequence[str] | None = None,
    ) -> TmdbMovieMetadata:
        """Return the movie's translations, keyed by 3-letter language code.

        Only translations are fetched: Radarr already supplies the title,
        overview, poster and genres, so the base movie record would add nothing.
        """

        payload = await self._request("GET", f"/movie/{tmdb_id}/translations")
        data = payload if isinstance(payload, dict) else {}

        return TmdbMovieMetadata(
            tmdb_id=self._safe_int(data.get("id")) or tmdb_id,
            translations=self._extract_translations(data, languages),
        )

    async def search_movies(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TmdbSearchResult]:
        params: dict[str, Any] = {"query": query, "include_adult": "false"}
        # Search accepts a single locale, so the first configured language wins
        # and TMDB falls back to the original title where it has no translation.
        language = self._search_language(languages)
        if language:
            params["language"] = language

        payload = await self._request("GET", "/search/movie", params=params)
        entries = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            return []

        results: list[TmdbSearchResult] = []
        for entry in entries[:limit]:
            if not isinstance(entry, dict):
                continue
            result = self._to_search_result(entry)
            if result is not None:
                results.append(result)
        return results

    def _to_search_result(self, entry: dict[str, Any]) -> TmdbSearchResult | None:
        tmdb_id = self._safe_int(entry.get("id"))
        if tmdb_id is None:
            return None
        title = self._safe_str(entry.get("title") or entry.get("original_title"))
        if not title:
            return None

        poster_path = self._safe_str(entry.get("poster_path"))
        original_title = self._safe_str(entry.get("original_title"))
        match_titles = (title,) if original_title is None else (title, original_title)
        return TmdbSearchResult(
            tmdb_id=tmdb_id,
            title=title,
            year=self._release_year(entry.get("release_date")),
            overview=self._safe_str(entry.get("overview")),
            poster_url=f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None,
            match_titles=tuple(dict.fromkeys(match_titles)),
            popularity=self._safe_int(entry.get("vote_count")) or 0,
        )

    def _search_language(self, languages: Sequence[str] | None) -> str | None:
        for language in languages or ():
            short = to_two_letter(language)
            if short:
                return short
        return None

    def _release_year(self, value: object) -> int | None:
        released = self._safe_str(value)
        if not released:
            return None
        return self._safe_int(released[:4])

    def _extract_translations(
        self,
        data: dict[str, Any],
        languages: Sequence[str] | None,
    ) -> dict[str, TmdbTranslation]:
        wanted = self._wanted_languages(languages)
        translations: dict[str, TmdbTranslation] = {}

        entries = data.get("translations")
        if not isinstance(entries, list):
            return translations

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            code = self._safe_str(entry.get("iso_639_1"))
            if not code:
                continue
            language = wanted.get(code.lower()) if wanted else self._canonical(code)
            if language is None:
                continue

            values = entry.get("data")
            if not isinstance(values, dict):
                continue
            title = self._safe_str(values.get("title"))
            overview = self._safe_str(values.get("overview"))
            if not title and not overview:
                continue

            translation = translations.get(language)
            if translation is None:
                translation = TmdbTranslation(language=language)
                translations[language] = translation
            # TMDB returns one entry per region (en-US, en-GB), so the fields are
            # filled independently and the first non-empty value of each wins.
            translation.title = translation.title or title
            translation.overview = translation.overview or overview

        return translations

    def _wanted_languages(self, languages: Sequence[str] | None) -> dict[str, str]:
        """Map TMDB's 2-letter codes back onto the codes the caller asked for."""

        wanted: dict[str, str] = {}
        for language in languages or []:
            if not language:
                continue
            short = to_two_letter(language)
            if short:
                wanted.setdefault(short, language)
        return wanted

    def _canonical(self, code: str) -> str:
        return TWO_TO_THREE_LETTER.get(code.lower(), code.lower())

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if self._auth_params:
            params = {**self._auth_params, **(kwargs.pop("params", None) or {})}
            kwargs["params"] = params
        return await self._http.request_json(method, path, **kwargs)

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


__all__ = ["TmdbHttpClient"]
