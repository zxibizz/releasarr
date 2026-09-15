"""HTTP client for TVDB metadata retrieval."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import httpx

from src.application.interfaces.tvdb import (
    TvdbSearchResult,
    TvdbSeriesMetadata,
    TvdbService,
    TvdbTranslation,
)
from src.core.logging import get_logger
from src.infrastructure.http import build_async_client

# TVDB models a season three times over - by broadcast order, by DVD order and
# by absolute numbering - and only the broadcast ("official") one lines up with
# the season numbers Sonarr works in.
OFFICIAL_SEASON_TYPE = "official"

# The one popularity figure TVDB will report for a search hit. /v4/search omits
# it and the v4 API offers no way to sort or batch by it, so the only alternative
# is a /series/{id} call per hit. This is the index behind thetvdb.com's own
# search box: undocumented, unversioned and unauthenticated, so it is treated as
# an enrichment that may vanish rather than as a source of results.
WEB_SEARCH_PATH = "/web/search/queries"
WEB_SEARCH_INDEX = "TVDB"


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
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._auth = _TvdbAuth(base_url=self._base_url, api_token=api_token)
        self._client = build_async_client(
            base_url=self._base_url,
            auth=self._auth,
            timeout=timeout_seconds,
            transport=transport,
        )
        self._auth.client = self._client
        # The web index sits beside the versioned API rather than under it.
        self._web_search_url = httpx.URL(self._base_url).copy_with(
            path=WEB_SEARCH_PATH,
            query=None,
            fragment=None,
        )
        self._logger = get_logger(component="tvdb")

    @property
    def is_configured(self) -> bool:
        return bool(self._api_token)

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
            seasons=self._extract_season_numbers(data),
        )

    async def search_series(
        self,
        query: str,
        limit: int = 20,
        languages: Sequence[str] | None = None,
    ) -> list[TvdbSearchResult]:
        # Concurrent, so the enrichment costs the difference between the two
        # rather than the sum.
        response, followers = await asyncio.gather(
            self._client.get(
                "/search",
                params={"query": query, "type": "series", "limit": limit},
            ),
            self._follower_counts(query, limit),
        )
        response.raise_for_status()
        payload = response.json()
        entries = payload.get("data") or []
        if not isinstance(entries, list):
            return []

        results: list[TvdbSearchResult] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            result = self._to_search_result(entry, languages, followers)
            if result is not None:
                results.append(result)
        return results

    async def _follower_counts(self, query: str, limit: int) -> dict[int, int] | None:
        """Follower counts for a search term, or ``None`` if the index will not say.

        Returning ``None`` rather than an empty mapping matters: the caller has a
        weaker popularity proxy to fall back on, and it must apply that proxy to
        every hit or none of them. Mixing the two scales in one result set would
        rank by which signal happened to be available.
        """

        try:
            response = await self._client.post(
                self._web_search_url,
                json={
                    "requests": [
                        {
                            "indexName": WEB_SEARCH_INDEX,
                            "params": {
                                "query": query,
                                "filters": "type:series",
                                "hitsPerPage": limit,
                            },
                        }
                    ]
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            self._logger.debug(
                "TVDB follower counts unavailable, ranking on translation breadth",
                error=str(exc),
                term=query,
            )
            return None

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list) or not results:
            return None

        counts: dict[int, int] = {}
        for result in results:
            hits = result.get("hits") if isinstance(result, dict) else None
            if not isinstance(hits, list):
                continue
            for hit in hits:
                if not isinstance(hit, dict):
                    continue
                tvdb_id = self._safe_int(hit.get("id"))
                followers = self._safe_int(hit.get("follower_count"))
                if tvdb_id is not None and followers is not None:
                    counts[tvdb_id] = followers
        return counts

    async def aclose(self) -> None:
        await self._client.aclose()

    def _to_search_result(
        self,
        entry: dict[str, object],
        languages: Sequence[str] | None,
        followers: dict[int, int] | None,
    ) -> TvdbSearchResult | None:
        # Search reports the id as a string, unlike every other TVDB endpoint.
        tvdb_id = self._safe_int(entry.get("tvdb_id") or entry.get("id"))
        if tvdb_id is None:
            return None

        translations = entry.get("translations")
        name = self._localized(translations, languages) or self._safe_str(entry.get("name"))
        if not name:
            return None
        overview = self._localized(entry.get("overviews"), languages) or self._safe_str(
            entry.get("overview")
        )

        return TvdbSearchResult(
            tvdb_id=tvdb_id,
            name=name,
            year=self._safe_int(entry.get("year")),
            overview=overview,
            image_url=self._safe_str(entry.get("image_url") or entry.get("thumbnail")),
            match_titles=self._match_titles(name, entry, translations),
            popularity=self._popularity(tvdb_id, translations, followers),
        )

    def _match_titles(
        self,
        name: str,
        entry: dict[str, object],
        translations: object,
    ) -> tuple[str, ...]:
        """Every title this entry is known by, display title first.

        Aliases are included even though they are the noisiest of the three: the
        abbreviation a user types ("GoT") often lives nowhere else.
        """

        candidates: list[str | None] = [name, self._safe_str(entry.get("name"))]
        if isinstance(translations, dict):
            candidates.extend(self._safe_str(value) for value in translations.values())
        aliases = entry.get("aliases")
        if isinstance(aliases, list):
            candidates.extend(self._safe_str(alias) for alias in aliases)

        seen: dict[str, None] = {}
        for candidate in candidates:
            if candidate:
                seen.setdefault(candidate, None)
        return tuple(seen)

    def _popularity(
        self,
        tvdb_id: int,
        translations: object,
        followers: dict[int, int] | None,
    ) -> int:
        """Followers where the index reported them, translation breadth otherwise.

        How widely a series has been translated tracks its following closely
        enough to order a result list by - a show translated into thirty
        languages outdraws a fan parody translated into one - and it is the only
        popularity signal /v4/search carries.
        """

        if followers is not None:
            return followers.get(tvdb_id, 0)
        if not isinstance(translations, dict):
            return 0
        return sum(1 for value in translations.values() if self._safe_str(value))

    def _localized(self, value: object, languages: Sequence[str] | None) -> str | None:
        """Pick the first configured language out of a search entry's translations.

        Search returns translations as a flat ``{language: text}`` mapping rather
        than the list of records the extended endpoint uses, so the configured
        order decides which one is shown.
        """

        if not isinstance(value, dict):
            return None
        for language in languages or ():
            translated = self._safe_str(value.get(language.lower()))
            if translated:
                return translated
        return None

    def _extract_season_numbers(self, data: dict[str, object]) -> list[int]:
        seasons = data.get("seasons")
        if not isinstance(seasons, list):
            return []

        numbers: set[int] = set()
        for season in seasons:
            if not isinstance(season, dict):
                continue
            season_type = season.get("type")
            type_name = (
                str(season_type.get("type") or "").lower() if isinstance(season_type, dict) else ""
            )
            if type_name and type_name != OFFICIAL_SEASON_TYPE:
                continue
            raw_number = season.get("number")
            if raw_number is None:
                raw_number = season.get("seasonNumber")
            number = self._safe_int(raw_number)
            if number is not None:
                numbers.add(number)
        return sorted(numbers)

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
