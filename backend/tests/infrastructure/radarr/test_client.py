"""Tests for the Radarr HTTP client's wanted list and manual import flow."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import patch

import httpx

from src.application.interfaces.radarr import MovieImportFile
from src.infrastructure.radarr import RadarrHttpClient
from src.infrastructure.radarr import client as radarr_client

IMPORT_FILE = MovieImportFile(
    path="/media/downloads/Arrival/arrival.2016.1080p.mkv",
    movie_id=42,
    folder_name="Arrival",
)

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


def build_client(handler: Handler) -> RadarrHttpClient:
    return RadarrHttpClient(
        base_url="https://radarr.example/api/v3",
        api_key="token",
        transport=httpx.MockTransport(handler),
    )


async def test_missing_movies_are_read_straight_off_the_wanted_list() -> None:
    """Radarr returns whole movie records, so no follow-up lookup is needed."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/wanted/missing")
        return httpx.Response(
            200,
            json={
                "page": 1,
                "totalRecords": 2,
                "records": [
                    {
                        "id": 156,
                        "title": "Arrival",
                        "year": 2016,
                        "overview": "Linguist meets heptapods.",
                        "runtime": 116,
                        "imdbId": "tt2543164",
                        "tmdbId": 329865,
                        "genres": ["Drama", "Science Fiction"],
                        "hasFile": False,
                        "images": [
                            {
                                "coverType": "poster",
                                "url": "/MediaCover/156/poster.jpg",
                                "remoteUrl": "https://image.tmdb.org/poster.jpg",
                            }
                        ],
                    },
                    # Radarr always sends an id; a record without one is unusable.
                    {"title": "Broken"},
                ],
            },
        )

    movies = await build_client(handler).get_missing_movies()

    assert len(movies) == 1
    movie = movies[0]
    assert movie.id == 156
    assert movie.title == "Arrival"
    assert movie.year == 2016
    assert movie.runtime_minutes == 116
    assert movie.imdb_id == "tt2543164"
    assert movie.tmdb_id == 329865
    assert movie.genres == ["Drama", "Science Fiction"]
    assert movie.has_file is False
    # The remote URL is preferred so the poster resolves without a Radarr session.
    assert movie.poster_url == "https://image.tmdb.org/poster.jpg"


async def test_get_movie_reports_whether_radarr_now_holds_the_file() -> None:
    """This is what closes a request after an import."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/movie/156")
        return httpx.Response(200, json={"id": 156, "title": "Arrival", "hasFile": True})

    movie = await build_client(handler).get_movie(156)

    assert movie.id == 156
    assert movie.has_file is True


async def test_manual_import_reprocesses_before_queueing_the_command() -> None:
    """The command overwrites metadata, so it has to carry the preview's values back."""

    calls: list[tuple[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append((request.url.path, json.loads(body) if body else None))

        if request.url.path.endswith("/manualimport"):
            return httpx.Response(
                200,
                json=[
                    {
                        "path": IMPORT_FILE.path,
                        "movieId": 42,
                        "quality": {"quality": {"id": 7, "name": "Bluray-1080p"}},
                        "languages": [{"id": 11, "name": "Russian"}],
                        "releaseGroup": "teko",
                        "indexerFlags": 0,
                    }
                ],
            )
        if request.url.path.endswith("/command/7"):
            return httpx.Response(200, json={"id": 7, "status": "completed"})
        return httpx.Response(201, json={"id": 7})

    client = build_client(handler)
    assert await client.manual_import([IMPORT_FILE]) is True

    assert [path for path, _ in calls] == [
        "/api/v3/manualimport",
        "/api/v3/command",
        "/api/v3/command/7",
    ]

    preview = calls[0][1]
    assert preview[0]["path"] == IMPORT_FILE.path
    assert preview[0]["movieId"] == 42
    assert preview[0]["quality"] == {"quality": {"id": 0}}
    assert preview[0]["languages"] == []

    command = calls[1][1]
    assert command["name"] == "ManualImport"
    # Copying leaves the torrent intact for seeding.
    assert command["importMode"] == "copy"
    assert command["files"] == [
        {
            "path": IMPORT_FILE.path,
            "movieId": 42,
            "folderName": "Arrival",
            "quality": {"quality": {"id": 7, "name": "Bluray-1080p"}},
            "languages": [{"id": 11, "name": "Russian"}],
            "releaseGroup": "teko",
            "indexerFlags": 0,
        }
    ]


async def test_manual_import_fails_when_radarr_cannot_read_the_file() -> None:
    """A rejected preview must stop the release from being recorded as exported."""

    command_calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal command_calls
        if request.url.path.endswith("/command"):
            command_calls += 1
            return httpx.Response(201, json={"id": 7})
        return httpx.Response(500, json={"message": "is not a valid *nix path"})

    client = build_client(handler)

    assert await client.manual_import([IMPORT_FILE]) is False
    assert command_calls == 0


async def test_manual_import_waits_for_the_queued_command_to_finish() -> None:
    """Radarr only queues the command, so accepting it is not the same as importing."""

    statuses = iter(("queued", "started", "completed"))
    polls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal polls
        if request.url.path.endswith("/manualimport"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/command/7"):
            polls += 1
            return httpx.Response(200, json={"id": 7, "status": next(statuses)})
        return httpx.Response(201, json={"id": 7})

    client = build_client(handler)

    with patch.object(radarr_client, "COMMAND_POLL_INTERVAL_SECONDS", 0):
        assert await client.manual_import([IMPORT_FILE]) is True

    assert polls == 3


async def test_manual_import_reports_a_command_radarr_could_not_run() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/manualimport"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/command/7"):
            return httpx.Response(200, json={"id": 7, "status": "failed"})
        return httpx.Response(201, json={"id": 7})

    client = build_client(handler)

    assert await client.manual_import([IMPORT_FILE]) is False
