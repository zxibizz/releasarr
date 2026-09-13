"""Tests for the Prowlarr-backed indexer directory."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from src.application.interfaces.indexers import IndexerNotFoundError
from src.infrastructure.http import HttpClientError
from src.infrastructure.prowlarr import ProwlarrIndexerDirectory

INDEXER_LIST = [
    {
        "id": 2,
        "name": "Zeta Tracker",
        "enable": True,
        "protocol": "torrent",
        "privacy": "private",
        "priority": 25,
        "supportsRss": True,
        "supportsSearch": True,
        "indexerUrls": ["https://zeta.example/"],
    },
    {
        "id": 1,
        "name": "Alpha Tracker",
        "enable": False,
        "protocol": "torrent",
        "privacy": "public",
        "priority": 50,
        "supportsRss": True,
        "supportsSearch": False,
        "indexerUrls": ["https://alpha.example/", "https://alpha.mirror/"],
    },
]


def _directory(handler: httpx.MockTransport) -> ProwlarrIndexerDirectory:
    return ProwlarrIndexerDirectory(
        base_url="https://prowlarr.example/api/v1",
        api_key="token",
        _transport=handler,
    )


@pytest.mark.asyncio
async def test_list_indexers_merges_the_separate_status_endpoint() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Api-Key"] == "token"
        if request.url.path.endswith("/indexerstatus"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 9,
                        "indexerId": 2,
                        "disabledTill": "2026-03-04T12:30:00Z",
                        "mostRecentFailure": "2026-03-04T00:30:00Z",
                        "initialFailure": "2026-03-03T18:00:00Z",
                    }
                ],
            )
        assert request.url.path.endswith("/indexer")
        return httpx.Response(200, json=INDEXER_LIST)

    directory = _directory(httpx.MockTransport(handler))
    records = await directory.list_indexers()

    assert [record.name for record in records] == ["Alpha Tracker", "Zeta Tracker"]

    alpha, zeta = records
    assert alpha.indexer_id == 1
    assert alpha.enabled is False
    assert alpha.supports_search is False
    assert alpha.indexer_urls == ("https://alpha.example/", "https://alpha.mirror/")
    assert alpha.disabled_till is None
    assert alpha.most_recent_failure is None

    assert zeta.indexer_id == 2
    assert zeta.enabled is True
    assert zeta.privacy == "private"
    assert zeta.priority == 25
    assert zeta.disabled_till == datetime(2026, 3, 4, 12, 30, tzinfo=UTC)
    assert zeta.initial_failure == datetime(2026, 3, 3, 18, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_list_indexers_treats_an_empty_status_list_as_healthy() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/indexerstatus"):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=INDEXER_LIST)

    directory = _directory(httpx.MockTransport(handler))
    records = await directory.list_indexers()

    assert all(record.disabled_till is None for record in records)
    assert all(record.most_recent_failure is None for record in records)
    assert all(record.initial_failure is None for record in records)


@pytest.mark.asyncio
async def test_list_indexers_skips_entries_without_an_id_or_name() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/indexerstatus"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json=[{"id": 1, "name": "Kept", "enable": True}, {"name": "No id"}, {"id": 3}],
        )

    directory = _directory(httpx.MockTransport(handler))
    records = await directory.list_indexers()

    assert [record.name for record in records] == ["Kept"]


@pytest.mark.asyncio
async def test_list_indexers_reports_an_upstream_refusal_as_a_client_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    directory = _directory(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError):
        await directory.list_indexers()


@pytest.mark.asyncio
async def test_test_indexer_posts_the_stored_definition_back() -> None:
    posted: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            assert request.url.path.endswith("/indexer/2")
            return httpx.Response(
                200,
                json={"id": 2, "name": "Zeta Tracker", "fields": [{"name": "apiKey"}]},
            )
        assert request.url.path.endswith("/indexer/test")
        posted.append(request.read().decode())
        return httpx.Response(200, text="{}")

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.test_indexer(2)

    assert result.success is True
    assert result.indexer_id == 2
    assert result.name == "Zeta Tracker"
    assert result.errors == ()
    # The definition round-trips untouched so Prowlarr can restore its secrets.
    assert '"id":2' in posted[0].replace(" ", "")
    assert "apiKey" in posted[0]


@pytest.mark.asyncio
async def test_test_indexer_reads_validation_failures_from_a_rejection() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"id": 2, "name": "Zeta Tracker"})
        return httpx.Response(
            400,
            json=[
                {"propertyName": "", "errorMessage": "Unable to connect to indexer"},
                {"propertyName": "apiKey", "errorMessage": "Invalid API key"},
            ],
        )

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.test_indexer(2)

    assert result.success is False
    assert result.errors == ("Unable to connect to indexer", "Invalid API key")


@pytest.mark.asyncio
async def test_test_indexer_raises_for_an_unknown_identifier() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not found"})

    directory = _directory(httpx.MockTransport(handler))

    with pytest.raises(IndexerNotFoundError):
        await directory.test_indexer(99)


@pytest.mark.asyncio
async def test_test_all_indexers_reads_the_body_of_a_400() -> None:
    """Prowlarr answers 400 as soon as one indexer fails, body intact."""

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/indexer/testall"):
            return httpx.Response(
                400,
                json=[
                    {"id": 1, "validationFailures": []},
                    {
                        "id": 2,
                        "validationFailures": [
                            {"propertyName": "", "errorMessage": "Request timed out"}
                        ],
                    },
                ],
            )
        if request.url.path.endswith("/indexerstatus"):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=INDEXER_LIST)

    directory = _directory(httpx.MockTransport(handler))
    results = await directory.test_all_indexers()

    assert [(result.indexer_id, result.success) for result in results] == [(1, True), (2, False)]
    assert results[0].name == "Alpha Tracker"
    assert results[1].name == "Zeta Tracker"
    assert results[1].errors == ("Request timed out",)


@pytest.mark.asyncio
async def test_test_all_indexers_maps_a_clean_run() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/indexer/testall"):
            return httpx.Response(200, json=[{"id": 2, "validationFailures": []}])
        if request.url.path.endswith("/indexerstatus"):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=INDEXER_LIST)

    directory = _directory(httpx.MockTransport(handler))
    results = await directory.test_all_indexers()

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].errors == ()
