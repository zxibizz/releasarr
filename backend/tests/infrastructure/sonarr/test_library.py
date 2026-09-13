"""Tests for the Sonarr HTTP client's library-management calls."""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import patch

import httpx

from src.infrastructure.http import HttpClientError
from src.infrastructure.sonarr import SonarrHttpClient
from src.infrastructure.sonarr import client as sonarr_client

Handler = Callable[[httpx.Request], Coroutine[None, None, httpx.Response]]

LOOKUP_PAYLOAD: dict[str, Any] = {
    "id": 0,
    "title": "Example Show",
    "titleSlug": "example-show",
    "year": 2020,
    "tvdbId": 555,
    "images": [{"coverType": "poster", "remoteUrl": "http://poster"}],
    "seasons": [
        {"seasonNumber": 0, "monitored": False},
        {"seasonNumber": 1, "monitored": False},
        {"seasonNumber": 2, "monitored": False},
    ],
}


def build_client(handler: Handler) -> SonarrHttpClient:
    return SonarrHttpClient(
        base_url="https://sonarr.example/api/v3",
        api_key="token",
        transport=httpx.MockTransport(handler),
    )


async def test_get_root_folders_skips_unusable_entries() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"path": "/tv", "freeSpace": 1024, "accessible": True},
                {"path": "/archive", "accessible": False},
                {"freeSpace": 99},
            ],
        )

    folders = await build_client(handler).get_root_folders()

    assert [(folder.path, folder.free_space, folder.accessible) for folder in folders] == [
        ("/tv", 1024, True),
        ("/archive", None, False),
    ]


async def test_get_root_folders_assumes_older_sonarr_folders_are_reachable() -> None:
    """``accessible`` is absent on older versions, where every folder is usable."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"path": "/tv"}])

    folders = await build_client(handler).get_root_folders()

    assert folders[0].accessible is True


async def test_get_quality_profiles_names_unnamed_profiles_by_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 4, "name": "Any"}, {"id": 7}, {"name": "No id"}])

    profiles = await build_client(handler).get_quality_profiles()

    assert [(profile.id, profile.name) for profile in profiles] == [(4, "Any"), (7, "7")]


async def test_search_series_reports_library_membership() -> None:
    """Sonarr marks a series it already holds with a non-zero id."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["term"] == "example"
        return httpx.Response(
            200,
            json=[
                {**LOOKUP_PAYLOAD, "id": 12, "seasons": [{"seasonNumber": 1, "monitored": True}]},
                {**LOOKUP_PAYLOAD, "tvdbId": 556},
                {"title": "No tvdb id"},
            ],
        )

    results = await build_client(handler).search_series("example")

    assert len(results) == 2
    assert results[0].existing_series_id == 12
    assert results[0].monitored_seasons == [1]
    # A series Sonarr does not hold arrives with id 0, which is not an id at all.
    assert results[1].existing_series_id is None
    assert results[1].monitored_seasons == []


async def test_lookup_series_queries_by_tvdb_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["term"] == "tvdb:555"
        return httpx.Response(200, json=[LOOKUP_PAYLOAD])

    lookup = await build_client(handler).lookup_series(555)

    assert lookup is not None
    assert lookup.tvdb_id == 555
    assert lookup.title == "Example Show"
    assert lookup.season_numbers == [0, 1, 2]


async def test_lookup_series_returns_none_when_sonarr_has_no_match() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    assert await build_client(handler).lookup_series(555) is None


async def test_add_series_monitors_only_the_requested_seasons() -> None:
    """The lookup payload goes back as it came, with the library fields filled in."""

    calls: list[tuple[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append((request.url.path, json.loads(body) if body else None))
        if request.url.path.endswith("/series/lookup"):
            return httpx.Response(200, json=[LOOKUP_PAYLOAD])
        return httpx.Response(201, json={"id": 12})

    series_id = await build_client(handler).add_series(
        tvdb_id=555,
        root_folder_path="/tv",
        quality_profile_id=4,
        monitored_seasons=[2],
    )

    assert series_id == 12
    payload = calls[1][1]
    assert payload["rootFolderPath"] == "/tv"
    assert payload["qualityProfileId"] == 4
    assert payload["monitored"] is True
    assert payload["seasonFolder"] is True
    # The slug and images Sonarr reported have to survive the round trip.
    assert payload["titleSlug"] == "example-show"
    assert payload["images"] == LOOKUP_PAYLOAD["images"]
    assert [(season["seasonNumber"], season["monitored"]) for season in payload["seasons"]] == [
        (0, False),
        (1, False),
        (2, True),
    ]
    # Episodes must be monitored or they stay out of Sonarr's wanted list, and
    # releasarr grabs through its own indexers rather than Sonarr's.
    assert payload["addOptions"] == {
        "monitor": "all",
        "searchForMissingEpisodes": False,
        "searchForCutoffUnmetEpisodes": False,
    }
    assert payload["monitorNewItems"] == "none"


async def test_add_series_can_ask_sonarr_for_future_seasons() -> None:
    calls: list[tuple[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append((request.url.path, json.loads(body) if body else None))
        if request.url.path.endswith("/series/lookup"):
            return httpx.Response(200, json=[LOOKUP_PAYLOAD])
        return httpx.Response(201, json={"id": 12})

    await build_client(handler).add_series(
        tvdb_id=555,
        root_folder_path="/tv",
        quality_profile_id=4,
        monitored_seasons=[2],
        monitor_new_seasons=True,
    )

    assert calls[1][1]["monitorNewItems"] == "all"


async def test_add_series_rejects_a_tvdb_id_sonarr_cannot_resolve() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    try:
        await build_client(handler).add_series(
            tvdb_id=555,
            root_folder_path="/tv",
            quality_profile_id=4,
            monitored_seasons=[1],
        )
    except HttpClientError as exc:
        assert "555" in str(exc)
    else:  # pragma: no cover - the call must not succeed
        raise AssertionError("expected an HttpClientError")


def build_monitoring_handler(
    calls: list[tuple[str, Any]],
    series: dict[str, Any],
) -> Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        calls.append((request.method, json.loads(body) if body else None))
        return httpx.Response(200, json=series)

    return handler


async def test_apply_season_monitoring_leaves_unnamed_seasons_alone() -> None:
    """A season monitored outside releasarr keeps whatever the user chose."""

    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {
            "id": 12,
            "monitored": False,
            "seasons": [
                {"seasonNumber": 1, "monitored": True},
                {"seasonNumber": 2, "monitored": False},
                {"seasonNumber": 3, "monitored": False},
            ],
        },
    )

    await build_client(handler).apply_season_monitoring(12, monitor=[3])

    assert [method for method, _ in calls] == ["GET", "PUT"]
    payload = calls[1][1]
    assert payload["monitored"] is True
    assert [(season["seasonNumber"], season["monitored"]) for season in payload["seasons"]] == [
        (1, True),
        (2, False),
        (3, True),
    ]


async def test_apply_season_monitoring_unmonitors_only_the_named_seasons() -> None:
    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {
            "id": 12,
            "monitored": True,
            "seasons": [
                {"seasonNumber": 1, "monitored": True},
                {"seasonNumber": 2, "monitored": True},
            ],
        },
    )

    await build_client(handler).apply_season_monitoring(12, unmonitor=[2])

    payload = calls[1][1]
    assert payload["monitored"] is True
    assert [(season["seasonNumber"], season["monitored"]) for season in payload["seasons"]] == [
        (1, True),
        (2, False),
    ]


async def test_apply_season_monitoring_leaves_the_series_monitored_with_nothing_left() -> None:
    """Releasarr keeps no series-level switch of its own.

    A monitored series with no monitored season is read by Sonarr as wanting
    nothing, so leaving the flag on costs nothing once the seasons have gone.
    """

    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {"id": 12, "monitored": True, "seasons": [{"seasonNumber": 1, "monitored": True}]},
    )

    await build_client(handler).apply_season_monitoring(12, unmonitor=[1])

    payload = calls[1][1]
    assert payload["monitored"] is True
    assert payload["seasons"][0]["monitored"] is False


async def test_apply_season_monitoring_monitors_a_series_that_was_switched_off() -> None:
    """Monitoring a season is pointless while the series it belongs to is off."""

    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {"id": 12, "monitored": False, "seasons": [{"seasonNumber": 1, "monitored": False}]},
    )

    await build_client(handler).apply_season_monitoring(12, monitor=[1])

    assert calls[1][1]["monitored"] is True


async def test_apply_season_monitoring_keeps_a_series_wanted_for_future_seasons() -> None:
    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {"id": 12, "monitored": True, "seasons": [{"seasonNumber": 1, "monitored": True}]},
    )

    await build_client(handler).apply_season_monitoring(
        12,
        unmonitor=[1],
        monitor_new_seasons=True,
    )

    payload = calls[1][1]
    assert payload["monitored"] is True
    assert payload["monitorNewItems"] == "all"


async def test_apply_season_monitoring_can_turn_future_seasons_off_on_its_own() -> None:
    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {
            "id": 12,
            "monitored": True,
            "monitorNewItems": "all",
            "seasons": [{"seasonNumber": 1, "monitored": True}],
        },
    )

    await build_client(handler).apply_season_monitoring(12, monitor_new_seasons=False)

    payload = calls[1][1]
    assert payload["monitorNewItems"] == "none"
    assert payload["monitored"] is True


async def test_apply_season_monitoring_skips_the_update_when_nothing_changes() -> None:
    calls: list[tuple[str, Any]] = []
    handler = build_monitoring_handler(
        calls,
        {
            "id": 12,
            "monitored": True,
            "monitorNewItems": "none",
            "seasons": [{"seasonNumber": 1, "monitored": True}],
        },
    )

    await build_client(handler).apply_season_monitoring(12, monitor=[1], unmonitor=[9])

    assert [method for method, _ in calls] == ["GET"]


async def test_series_details_report_whether_future_seasons_are_wanted() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": 12,
                "title": "Example",
                "monitorNewItems": "all",
                "seasons": [{"seasonNumber": 1, "monitored": True}],
            },
        )

    details = await build_client(handler).get_series(12)

    assert details.monitor_new_seasons is True


async def test_wait_for_series_episodes_polls_until_sonarr_has_refreshed() -> None:
    """A series added a moment ago reports no episodes until its refresh lands."""

    responses = [
        {"id": 12, "seasons": [{"seasonNumber": 1, "statistics": {"totalEpisodeCount": 0}}]},
        {"id": 12, "seasons": [{"seasonNumber": 1, "statistics": {"totalEpisodeCount": 8}}]},
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0) if len(responses) > 1 else responses[0])

    with patch.object(sonarr_client, "REFRESH_POLL_INTERVAL_SECONDS", 0):
        details = await build_client(handler).wait_for_series_episodes(12, [1])

    assert details.seasons[1].total_episode_count == 8


async def test_wait_for_series_episodes_gives_up_without_failing() -> None:
    """Timing out leaves a stale count, which the next sync fixes; failing would not."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": 12, "seasons": [{"seasonNumber": 1, "statistics": {}}]},
        )

    details = await build_client(handler).wait_for_series_episodes(12, [1], timeout_seconds=0.0)

    assert details.seasons[1].total_episode_count == 0
