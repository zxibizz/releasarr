"""Tests for the TMDB client's translation lookup and language-code mapping."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx

from src.infrastructure.tmdb import TmdbHttpClient

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]

TRANSLATIONS = {
    "id": 329865,
    "translations": [
        {
            "iso_3166_1": "US",
            "iso_639_1": "en",
            "data": {"title": "Arrival", "overview": "Linguist meets heptapods."},
        },
        {
            "iso_3166_1": "RU",
            "iso_639_1": "ru",
            "data": {"title": "Прибытие", "overview": "Лингвист встречает гептаподов."},
        },
        {
            "iso_3166_1": "FR",
            "iso_639_1": "fr",
            "data": {"title": "Premier Contact", "overview": "Une linguiste."},
        },
    ],
}


def build_client(handler: Handler, api_token: str = "0123456789abcdef") -> TmdbHttpClient:
    return TmdbHttpClient(
        base_url="https://api.themoviedb.org/3",
        api_token=api_token,
        transport=httpx.MockTransport(handler),
    )


async def test_translations_are_keyed_by_the_requested_language_codes() -> None:
    """Movie localizations must use the same 3-letter keys series localizations do."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/movie/329865/translations")
        return httpx.Response(200, json=TRANSLATIONS)

    metadata = await build_client(handler).get_movie(329865, ["rus", "eng"])

    assert metadata.tmdb_id == 329865
    assert sorted(metadata.translations) == ["eng", "rus"]
    assert metadata.translations["rus"].title == "Прибытие"
    assert metadata.translations["eng"].overview == "Linguist meets heptapods."


async def test_languages_not_asked_for_are_dropped() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=TRANSLATIONS)

    metadata = await build_client(handler).get_movie(329865, ["eng"])

    assert list(metadata.translations) == ["eng"]


async def test_every_language_is_kept_when_none_are_requested() -> None:
    """Without a filter the codes still have to be widened to their 3-letter form."""

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=TRANSLATIONS)

    metadata = await build_client(handler).get_movie(329865)

    assert sorted(metadata.translations) == ["eng", "fra", "rus"]


async def test_regional_variants_fill_each_other_s_gaps() -> None:
    """TMDB sends one entry per region, and either may be the one with a title."""

    payload = {
        "id": 1,
        "translations": [
            {"iso_639_1": "en", "data": {"title": "", "overview": "A US overview."}},
            {"iso_639_1": "en", "data": {"title": "The Movie", "overview": ""}},
            # Neither field is usable, so this must not create a language entry.
            {"iso_639_1": "de", "data": {"title": "", "overview": ""}},
        ],
    }

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    metadata = await build_client(handler).get_movie(1, ["eng", "deu"])

    assert list(metadata.translations) == ["eng"]
    assert metadata.translations["eng"].title == "The Movie"
    assert metadata.translations["eng"].overview == "A US overview."


async def test_a_v3_key_travels_in_the_query_string() -> None:
    captured: list[httpx.URL] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url)
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=TRANSLATIONS)

    await build_client(handler, api_token="0123456789abcdef").get_movie(329865)

    assert captured[0].params["api_key"] == "0123456789abcdef"


async def test_a_v4_read_token_travels_in_the_authorization_header() -> None:
    """The v4 token is a JWT, which TMDB only accepts as a bearer credential."""

    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=TRANSLATIONS)

    await build_client(handler, api_token="header.payload.signature").get_movie(329865)

    assert captured[0].headers["Authorization"] == "Bearer header.payload.signature"
    assert "api_key" not in captured[0].url.params
