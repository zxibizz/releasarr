"""Tests for the TMDB client's movie title search."""

from __future__ import annotations

from collections.abc import Callable, Coroutine

import httpx

from src.infrastructure.tmdb import TmdbHttpClient

Handler = Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]

SEARCH_RESULTS = {
    "results": [
        {
            "id": 329865,
            "title": "Arrival",
            "original_title": "Arrival",
            "overview": "Linguist meets heptapods.",
            "release_date": "2016-11-10",
            "poster_path": "/poster.jpg",
        },
        {
            "id": 1,
            "original_title": "Untitled",
            "release_date": "",
            "poster_path": None,
        },
        {"title": "No id"},
    ]
}


def build_client(handler: Handler) -> TmdbHttpClient:
    return TmdbHttpClient(
        base_url="https://api.themoviedb.org/3",
        api_token="0123456789abcdef",
        transport=httpx.MockTransport(handler),
    )


async def test_search_movies_builds_absolute_poster_urls() -> None:
    """TMDB serves images from a separate host and reports only the path."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/3/search/movie"
        assert request.url.params["query"] == "arrival"
        return httpx.Response(200, json=SEARCH_RESULTS)

    results = await build_client(handler).search_movies("arrival")

    assert len(results) == 2
    assert results[0].tmdb_id == 329865
    assert results[0].title == "Arrival"
    assert results[0].year == 2016
    assert results[0].poster_url == "https://image.tmdb.org/t/p/w500/poster.jpg"
    # A movie with neither a poster nor a release date is still usable.
    assert results[1].title == "Untitled"
    assert results[1].year is None
    assert results[1].poster_url is None


async def test_search_movies_asks_for_the_first_configured_language() -> None:
    """Search takes a single locale, so the configured order decides which."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["language"] == "ru"
        return httpx.Response(200, json={"results": []})

    await build_client(handler).search_movies("arrival", languages=("rus", "eng"))


async def test_search_movies_omits_the_language_when_none_maps_to_tmdb() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "language" not in request.url.params
        return httpx.Response(200, json={"results": []})

    await build_client(handler).search_movies("arrival", languages=("qqq",))


async def test_search_movies_keeps_the_original_title_for_ranking() -> None:
    """The localized title may share nothing with the term the user typed."""

    payload = {
        "results": [
            {
                "id": 546121,
                "title": "Игра престолов: Последний дозор",
                "original_title": "Game of Thrones: The Last Watch",
            },
            {"id": 2, "title": "Arrival", "original_title": "Arrival"},
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    results = await build_client(handler).search_movies("game of thrones")

    assert results[0].match_titles == (
        "Игра престолов: Последний дозор",
        "Game of Thrones: The Last Watch",
    )
    # An untranslated movie has one title, not the same one twice.
    assert results[1].match_titles == ("Arrival",)


async def test_search_movies_reports_the_vote_count_as_popularity() -> None:
    payload = {
        "results": [
            {"id": 1, "title": "Widely rated", "vote_count": 354},
            {"id": 2, "title": "Barely rated", "vote_count": 2},
            {"id": 3, "title": "Unrated"},
        ]
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    results = await build_client(handler).search_movies("rated")

    assert [result.popularity for result in results] == [354, 2, 0]


async def test_search_movies_honours_the_limit() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SEARCH_RESULTS)

    results = await build_client(handler).search_movies("arrival", limit=1)

    assert len(results) == 1
