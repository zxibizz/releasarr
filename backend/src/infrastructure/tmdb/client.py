"""HTTP client for TMDB metadata retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from src.application.interfaces.tmdb import TmdbMovieMetadata, TmdbService, TmdbTranslation
from src.infrastructure.http import BaseHttpClient

# TMDB reports languages as ISO 639-1, while requests store their localizations
# under the 3-letter codes TVDB uses, so movie and series entries stay
# interchangeable in the UI. Both the terminological and the bibliographic
# 3-letter form are accepted, since either may appear in configuration.
LANGUAGE_ALIASES: dict[str, str] = {
    "ara": "ar",
    "bul": "bg",
    "cat": "ca",
    "ces": "cs",
    "cze": "cs",
    "chi": "zh",
    "dan": "da",
    "deu": "de",
    "dut": "nl",
    "ell": "el",
    "eng": "en",
    "est": "et",
    "fas": "fa",
    "fin": "fi",
    "fra": "fr",
    "fre": "fr",
    "ger": "de",
    "gre": "el",
    "heb": "he",
    "hin": "hi",
    "hrv": "hr",
    "hun": "hu",
    "ind": "id",
    "ita": "it",
    "jpn": "ja",
    "kor": "ko",
    "lav": "lv",
    "lit": "lt",
    "nld": "nl",
    "nor": "no",
    "per": "fa",
    "pol": "pl",
    "por": "pt",
    "ron": "ro",
    "rum": "ro",
    "rus": "ru",
    "slk": "sk",
    "slo": "sk",
    "slv": "sl",
    "spa": "es",
    "srp": "sr",
    "swe": "sv",
    "tha": "th",
    "tur": "tr",
    "ukr": "uk",
    "vie": "vi",
    "zho": "zh",
}

# Used when no language filter is supplied and a 2-letter code has to be widened
# back to the 3-letter form requests are keyed by.
CANONICAL_LANGUAGES: dict[str, str] = {
    "ar": "ara",
    "bg": "bul",
    "ca": "cat",
    "cs": "ces",
    "da": "dan",
    "de": "deu",
    "el": "ell",
    "en": "eng",
    "es": "spa",
    "et": "est",
    "fa": "fas",
    "fi": "fin",
    "fr": "fra",
    "he": "heb",
    "hi": "hin",
    "hr": "hrv",
    "hu": "hun",
    "id": "ind",
    "it": "ita",
    "ja": "jpn",
    "ko": "kor",
    "lt": "lit",
    "lv": "lav",
    "nl": "nld",
    "no": "nor",
    "pl": "pol",
    "pt": "por",
    "ro": "ron",
    "ru": "rus",
    "sk": "slk",
    "sl": "slv",
    "sr": "srp",
    "sv": "swe",
    "th": "tha",
    "tr": "tur",
    "uk": "ukr",
    "vi": "vie",
    "zh": "zho",
}


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
            requested = language.strip().lower()
            short = LANGUAGE_ALIASES.get(requested, requested if len(requested) == 2 else None)
            if short:
                wanted.setdefault(short, language)
        return wanted

    def _canonical(self, code: str) -> str:
        return CANONICAL_LANGUAGES.get(code.lower(), code.lower())

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
