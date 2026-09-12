"""Tests for the Sonarr HTTP client's manual import flow."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import patch

import httpx

from src.application.interfaces.sonarr import ManualImportFile
from src.infrastructure.sonarr import SonarrHttpClient
from src.infrastructure.sonarr import client as sonarr_client

IMPORT_FILE = ManualImportFile(
    path="/media/downloads/Avatar/Season_01/s01e19.avi",
    series_id=42,
    episode_ids=[419],
    folder_name="Avatar",
)

Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


def build_client(handler: Handler) -> SonarrHttpClient:
    return SonarrHttpClient(
        base_url="https://sonarr.example/api/v3",
        api_key="token",
        transport=httpx.MockTransport(handler),
    )


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
                        "seriesId": 42,
                        "quality": {"quality": {"id": 9, "name": "HDTV-1080p"}},
                        "languages": [{"id": 11, "name": "Russian"}],
                        "releaseGroup": "teko",
                        "indexerFlags": 0,
                        "releaseType": "singleEpisode",
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
    assert preview[0]["episodeIds"] == [419]
    assert preview[0]["quality"] == {"quality": {"id": 0}}
    assert preview[0]["languages"] == []

    command = calls[1][1]
    assert command["name"] == "ManualImport"
    assert command["importMode"] == "copy"
    assert command["files"] == [
        {
            "path": IMPORT_FILE.path,
            "seriesId": 42,
            "episodeIds": [419],
            "folderName": "Avatar",
            "quality": {"quality": {"id": 9, "name": "HDTV-1080p"}},
            "languages": [{"id": 11, "name": "Russian"}],
            "releaseGroup": "teko",
            "indexerFlags": 0,
            "releaseType": "singleEpisode",
        }
    ]


async def test_manual_import_fails_when_sonarr_cannot_read_the_file() -> None:
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
    """Sonarr only queues the command, so accepting it is not the same as importing."""

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

    with patch.object(sonarr_client, "COMMAND_POLL_INTERVAL_SECONDS", 0):
        assert await client.manual_import([IMPORT_FILE]) is True

    assert polls == 3


async def test_manual_import_reports_a_command_sonarr_could_not_run() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/manualimport"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/command/7"):
            return httpx.Response(200, json={"id": 7, "status": "failed"})
        return httpx.Response(201, json={"id": 7})

    client = build_client(handler)

    assert await client.manual_import([IMPORT_FILE]) is False
