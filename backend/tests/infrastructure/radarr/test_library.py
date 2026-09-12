"""Tests for the Radarr HTTP client's library-management calls."""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from typing import Any

import httpx

from src.infrastructure.http import HttpClientError
from src.infrastructure.radarr import RadarrHttpClient

Handler = Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]

LOOKUP_PAYLOAD: dict[str, Any] = {
    "id": 0,
    "title": "Example Movie",
    "titleSlug": "example-movie",
    "year": 2021,
    "tmdbId": 777,
    "images": [{"coverType": "poster", "remoteUrl": "http://poster"}],
}


def build_client(handler: Handler) -> RadarrHttpClient:
    return RadarrHttpClient(
        base_url="https://radarr.example/api/v3",
        api_key="token",
        transport=httpx.MockTransport(handler),
    )


async def test_get_root_folders_reports_free_space() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"path": "/movies", "freeSpace": 2048}])

    folders = await build_client(handler).get_root_folders()

    assert [(folder.path, folder.free_space) for folder in folders] == [("/movies", 2048)]


async def test_get_quality_profiles_skips_entries_without_an_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"name": "No id"}, {"id": 2, "name": "HD"}])

    profiles = await build_client(handler).get_quality_profiles()

    assert [(profile.id, profile.name) for profile in profiles] == [(2, "HD")]


async def test_search_movies_reports_library_membership() -> None:
    """Radarr marks a movie it already holds with a non-zero id."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["term"] == "example"
        return httpx.Response(
            200,
            json=[
                {**LOOKUP_PAYLOAD, "id": 31},
                {**LOOKUP_PAYLOAD, "tmdbId": 778},
                {"title": "No tmdb id"},
            ],
        )

    results = await build_client(handler).search_movies("example")

    assert len(results) == 2
    assert results[0].existing_movie_id == 31
    assert results[1].existing_movie_id is None


async def test_lookup_movie_queries_by_tmdb_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["term"] == "tmdb:777"
        return httpx.Response(200, json=[LOOKUP_PAYLOAD])

    lookup = await build_client(handler).lookup_movie(777)

    assert lookup is not None
    assert lookup.tmdb_id == 777
    assert lookup.title == "Example Movie"
    assert lookup.year == 2021


async def test_lookup_movie_returns_none_when_radarr_has_no_match() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    assert await build_client(handler).lookup_movie(777) is None


async def test_add_movie_sends_the_lookup_payload_back_with_library_fields() -> None:
    calls: list[tuple[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append((request.url.path, json.loads(body) if body else None))
        if request.url.path.endswith("/movie/lookup"):
            return httpx.Response(200, json=[LOOKUP_PAYLOAD])
        return httpx.Response(201, json={"id": 31})

    movie_id = await build_client(handler).add_movie(
        tmdb_id=777,
        root_folder_path="/movies",
        quality_profile_id=2,
    )

    assert movie_id == 31
    payload = calls[1][1]
    assert payload["rootFolderPath"] == "/movies"
    assert payload["qualityProfileId"] == 2
    assert payload["monitored"] is True
    assert payload["titleSlug"] == "example-movie"
    # A stricter availability would keep the movie out of Radarr's wanted list,
    # and releasarr grabs through its own indexers rather than Radarr's.
    assert payload["minimumAvailability"] == "released"
    assert payload["addOptions"] == {"searchForMovie": False}


async def test_add_movie_rejects_a_tmdb_id_radarr_cannot_resolve() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    try:
        await build_client(handler).add_movie(
            tmdb_id=777,
            root_folder_path="/movies",
            quality_profile_id=2,
        )
    except HttpClientError as exc:
        assert "777" in str(exc)
    else:  # pragma: no cover - the call must not succeed
        raise AssertionError("expected an HttpClientError")


async def test_set_movie_monitored_updates_an_unmonitored_movie() -> None:
    calls: list[tuple[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append((request.method, json.loads(body) if body else None))
        return httpx.Response(200, json={"id": 31, "monitored": False})

    await build_client(handler).set_movie_monitored(31)

    assert [method for method, _ in calls] == ["GET", "PUT"]
    assert calls[1][1]["monitored"] is True


async def test_set_movie_monitored_skips_the_update_when_already_monitored() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(200, json={"id": 31, "monitored": True})

    await build_client(handler).set_movie_monitored(31)

    assert calls == ["GET"]
