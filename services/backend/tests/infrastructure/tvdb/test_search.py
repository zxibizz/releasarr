"""Tests for the TVDB client's series search and season extraction."""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine

import httpx

from src.infrastructure.tvdb import TvdbHttpClient
from src.infrastructure.tvdb.client import WEB_SEARCH_PATH

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
            "aliases": ["GoT", "Le Trône de fer"],
        },
        {"tvdb_id": "1", "name": "No translations"},
        {"name": "No id"},
    ]
}


def search_payload(*entries: dict[str, object]) -> dict[str, object]:
    return {"data": list(entries)}


def build_client(
    handler: Handler,
    followers: dict[int, int] | None = None,
    web_requests: list[httpx.Request] | None = None,
) -> TvdbHttpClient:
    """A client whose `/v4/search` is `handler`.

    The follower-count index is answered separately, and refuses by default so
    that the tests which do not care about it exercise the fallback.
    """

    async def with_login(request: httpx.Request) -> httpx.Response:
        # Every TVDB call is preceded by a bearer-token login on the first request.
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"data": {"token": "bearer-token"}})
        assert request.headers["Authorization"] == "Bearer bearer-token"
        if request.url.path == WEB_SEARCH_PATH:
            if web_requests is not None:
                web_requests.append(request)
            if followers is None:
                return httpx.Response(503, json={"message": "nope"})
            hits = [{"id": key, "follower_count": value} for key, value in followers.items()]
            return httpx.Response(200, json={"results": [{"hits": hits}]})
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


async def test_search_series_collects_every_title_the_entry_is_known_by() -> None:
    """Ranking scores these, so a Russian display title must not hide the rest."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SEARCH_RESULTS)

    results = await build_client(handler).search_series("thrones", languages=("rus", "eng"))

    assert results[0].match_titles == (
        "Игра престолов",
        "Game of Thrones",
        "GoT",
        "Le Trône de fer",
    )
    assert results[1].match_titles == ("No translations",)


async def test_search_series_reports_the_follower_count_as_popularity() -> None:
    """`/v4/search` omits followers, so they come from the index behind the website."""

    payload = search_payload(
        {"tvdb_id": "121361", "name": "Game of Thrones"},
        {"tvdb_id": "2", "name": "Game of Thrones Talk"},
        # Absent from the index, which only ranks it last among these three.
        {"tvdb_id": "3", "name": "Game of Thrones Cartoon Parody"},
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    web_requests: list[httpx.Request] = []
    client = build_client(handler, followers={121361: 6631485, 2: 1305}, web_requests=web_requests)
    results = await client.search_series("game of thrones", limit=5)

    assert [result.popularity for result in results] == [6631485, 1305, 0]
    assert json.loads(web_requests[0].content) == {
        "requests": [
            {
                "indexName": "TVDB",
                "params": {
                    "query": "game of thrones",
                    "filters": "type:series",
                    "hitsPerPage": 5,
                },
            }
        ]
    }


async def test_search_series_falls_back_to_translation_breadth_for_popularity() -> None:
    """An undocumented index may stop answering; the search must not stop with it."""

    payload = search_payload(
        {
            "tvdb_id": "1",
            "name": "Widely translated",
            "translations": {str(index): f"Title {index}" for index in range(10)},
        },
        {
            "tvdb_id": "2",
            "name": "Somewhat translated",
            "translations": {str(index): f"Title {index}" for index in range(4)},
        },
        {"tvdb_id": "3", "name": "Barely translated", "translations": {"rus": "Название"}},
        {"tvdb_id": "4", "name": "Untranslated"},
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    # build_client refuses the follower index unless asked to answer.
    results = await build_client(handler).search_series("translated")

    assert [result.popularity for result in results] == [10, 4, 1, 0]


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
