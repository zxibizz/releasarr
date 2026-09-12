"""Tests for the TVDB client's series search and season extraction."""

from __future__ import annotations

from collections.abc import Callable, Coroutine

import httpx

from src.infrastructure.tvdb import TvdbHttpClient

Handler = Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]

SEARCH_RESULTS = {
    "data": [
        {
            "objectID": "series-121361",
            # Search reports the id as a string, unlike every other endpoint.
            "tvdb_id": "121361",
            "name": "Game of Thrones",
            "overview": "Noble families fight for control.",
            "year": "2011",
            "image_url": "http://tvdb/got.jpg",
            "translations": {"rus": "Игра престолов"},
            "overviews": {"rus": "Знатные семьи борются за власть."},
        },
        {"tvdb_id": "1", "name": "No translations"},
        {"name": "No id"},
    ]
}


def build_client(handler: Handler) -> TvdbHttpClient:
    async def with_login(request: httpx.Request) -> httpx.Response:
        # Every TVDB call is preceded by a bearer-token login on the first request.
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"data": {"token": "bearer-token"}})
        assert request.headers["Authorization"] == "Bearer bearer-token"
        return await handler(request)

    return TvdbHttpClient(
        base_url="https://api4.thetvdb.com/v4",
        api_token="token",
        transport=httpx.MockTransport(with_login),
    )


async def test_search_series_prefers_the_configured_language() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v4/search"
        assert request.url.params["query"] == "thrones"
        assert request.url.params["type"] == "series"
        return httpx.Response(200, json=SEARCH_RESULTS)

    results = await build_client(handler).search_series("thrones", languages=("rus", "eng"))

    assert len(results) == 2
    assert results[0].tvdb_id == 121361
    assert results[0].name == "Игра престолов"
    assert results[0].overview == "Знатные семьи борются за власть."
    assert results[0].year == 2011
    assert results[0].image_url == "http://tvdb/got.jpg"


async def test_search_series_falls_back_to_the_default_name() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SEARCH_RESULTS)

    results = await build_client(handler).search_series("thrones", languages=("fra",))

    assert results[0].name == "Game of Thrones"
    assert results[1].name == "No translations"


async def test_get_series_reports_only_broadcast_season_numbers() -> None:
    """TVDB models seasons three times over, and only "official" matches Sonarr."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": 121361,
                    "name": "Game of Thrones",
                    "seasons": [
                        {"id": 1, "number": 0, "type": {"type": "official"}},
                        {"id": 2, "number": 1, "type": {"type": "official"}},
                        {"id": 3, "number": 2, "type": {"type": "official"}},
                        {"id": 4, "number": 1, "type": {"type": "dvd"}},
                        {"id": 5, "number": 1, "type": {"type": "absolute"}},
                    ],
                }
            },
        )

    metadata = await build_client(handler).get_series(121361)

    # Specials are season 0, which a falsy check would drop.
    assert metadata.seasons == [0, 1, 2]
