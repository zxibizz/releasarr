"""Tests for the Prowlarr-backed indexer directory."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from src.application.interfaces.indexers import IndexerNotFoundError
from src.domain.enums import IndexerEventType, IndexerLogLevel
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


HISTORY_PAGE = {
    "page": 1,
    "pageSize": 2,
    "totalRecords": 57,
    "records": [
        {
            "id": 412,
            "indexerId": 2,
            "indexerName": "Zeta Tracker",
            "date": "2026-03-04T11:59:00Z",
            "successful": True,
            "eventType": "indexerQuery",
            "data": {
                "query": "Severance S02",
                "queryResults": "39",
                "elapsedTime": "412",
                "source": "Sonarr",
                "host": "sonarr.example",
            },
        },
        {
            "id": 411,
            "indexerId": 1,
            "indexerName": "Alpha Tracker",
            "date": "2026-03-04T11:40:00Z",
            "successful": False,
            "eventType": "releaseGrabbed",
            "data": {"grabTitle": "Severance.S02E01.2160p", "source": "Prowlarr"},
        },
    ],
}


@pytest.mark.asyncio
async def test_list_history_asks_prowlarr_for_the_page_and_lifts_the_useful_data() -> None:
    seen: list[httpx.URL] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json=HISTORY_PAGE)

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.list_history(page=3, per_page=25)

    params = seen[0].params
    assert params["page"] == "3"
    assert params["pageSize"] == "25"
    # Prowlarr's default sort is not chronological, and the UI reads newest first.
    assert params["sortKey"] == "date"
    assert params["sortDirection"] == "descending"

    assert result.total == 57

    query, grab = result.events
    assert query.event_id == 412
    assert query.indexer_id == 2
    assert query.indexer_name == "Zeta Tracker"
    assert query.occurred_at == datetime(2026, 3, 4, 11, 59, tzinfo=UTC)
    assert query.event_type is IndexerEventType.INDEXER_QUERY
    assert query.successful is True
    assert query.query == "Severance S02"
    assert query.source == "Sonarr"
    assert query.elapsed_ms == 412
    # Lifted fields are not repeated in the leftover data.
    assert query.data == {"queryResults": "39", "host": "sonarr.example"}

    assert grab.event_type is IndexerEventType.RELEASE_GRABBED
    assert grab.successful is False
    assert grab.title == "Severance.S02E01.2160p"
    assert grab.query is None


@pytest.mark.asyncio
async def test_list_history_passes_the_filters_in_prowlarrs_own_vocabulary() -> None:
    seen: list[httpx.URL] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json={"records": [], "totalRecords": 0})

    directory = _directory(httpx.MockTransport(handler))
    await directory.list_history(
        page=1,
        per_page=20,
        indexer_id=2,
        event_type=IndexerEventType.INDEXER_RSS,
    )

    params = seen[0].params
    assert params["indexerIds"] == "2"
    assert params["eventType"] == "indexerRss"


@pytest.mark.asyncio
async def test_list_history_keeps_an_event_type_it_does_not_recognise() -> None:
    """A newer Prowlarr adding an event type should not drop the row."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalRecords": 1,
                "records": [
                    {
                        "id": 5,
                        "indexerId": 2,
                        "date": "2026-03-04T11:00:00Z",
                        "eventType": "indexerSomethingNew",
                    }
                ],
            },
        )

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.list_history(page=1, per_page=20)

    assert result.events[0].event_type is IndexerEventType.UNKNOWN


@pytest.mark.asyncio
async def test_list_history_skips_records_missing_what_identifies_them() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalRecords": 3,
                "records": [
                    {"id": 1, "indexerId": 2, "date": "2026-03-04T11:00:00Z"},
                    {"indexerId": 2, "date": "2026-03-04T11:00:00Z"},
                    {"id": 3, "indexerId": 2, "date": "not a date"},
                ],
            },
        )

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.list_history(page=1, per_page=20)

    assert [event.event_id for event in result.events] == [1]


@pytest.mark.asyncio
async def test_list_history_reports_an_upstream_refusal_as_a_client_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "Boom"})

    directory = _directory(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError):
        await directory.list_history(page=1, per_page=20)


LOG_PAGE = {
    "page": 1,
    "pageSize": 2,
    "totalRecords": 318,
    "records": [
        {
            "id": 9001,
            "time": "2026-03-04T11:59:00Z",
            "level": "info",
            "logger": "ReleaseSearchService",
            "message": "Searching indexer(s): [RuTracker.org] for Term: [Chad Powers]",
        },
        {
            "id": 9000,
            "time": "2026-03-04T11:58:00Z",
            "level": "warn",
            "logger": "RuTracker",
            "message": "Request for RuTracker.org failed with status 525.",
            "method": "GET",
            "exception": "System.Net.Http.HttpRequestException: boom",
            "exceptionType": "System.Net.Http.HttpRequestException",
        },
    ],
}


@pytest.mark.asyncio
async def test_list_logs_asks_prowlarr_for_the_page_newest_first() -> None:
    seen: list[httpx.URL] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json=LOG_PAGE)

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.list_logs(page=2, per_page=50)

    assert seen[0].path.endswith("/log")
    params = seen[0].params
    assert params["page"] == "2"
    assert params["pageSize"] == "50"
    assert params["sortKey"] == "time"
    assert params["sortDirection"] == "descending"

    assert result.total == 318

    info, warning = result.logs
    assert info.log_id == 9001
    assert info.occurred_at == datetime(2026, 3, 4, 11, 59, tzinfo=UTC)
    assert info.level is IndexerLogLevel.INFO
    assert info.component == "ReleaseSearchService"
    assert info.message.startswith("Searching indexer(s)")
    assert info.exception is None

    assert warning.level is IndexerLogLevel.WARN
    assert warning.component == "RuTracker"
    assert warning.method == "GET"
    assert warning.exception == "System.Net.Http.HttpRequestException: boom"
    assert warning.exception_type == "System.Net.Http.HttpRequestException"


@pytest.mark.asyncio
async def test_list_logs_sends_the_level_capitalised_as_prowlarr_stores_it() -> None:
    """Prowlarr lower-cases the level it reports but compares the stored value."""

    seen: list[httpx.URL] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url)
        return httpx.Response(200, json={"records": [], "totalRecords": 0})

    directory = _directory(httpx.MockTransport(handler))
    await directory.list_logs(page=1, per_page=20, min_level=IndexerLogLevel.WARN)

    assert seen[0].params["level"] == "Warn"


@pytest.mark.asyncio
async def test_list_logs_keeps_an_entry_whose_only_content_is_its_exception() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalRecords": 1,
                "records": [
                    {
                        "id": 1,
                        "time": "2026-03-04T11:00:00Z",
                        "level": "error",
                        "exception": "at Prowlarr.Core.Something()",
                        "exceptionType": "System.InvalidOperationException",
                    }
                ],
            },
        )

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.list_logs(page=1, per_page=20)

    entry = result.logs[0]
    assert entry.message == "System.InvalidOperationException"
    assert entry.exception == "at Prowlarr.Core.Something()"


@pytest.mark.asyncio
async def test_list_logs_reads_a_level_it_does_not_define_as_info() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "totalRecords": 2,
                "records": [
                    {"id": 1, "time": "2026-03-04T11:00:00Z", "level": "warning", "message": "a"},
                    {"id": 2, "time": "2026-03-04T10:00:00Z", "level": "whatever", "message": "b"},
                ],
            },
        )

    directory = _directory(httpx.MockTransport(handler))
    result = await directory.list_logs(page=1, per_page=20)

    assert [entry.level for entry in result.logs] == [IndexerLogLevel.WARN, IndexerLogLevel.INFO]


@pytest.mark.asyncio
async def test_list_logs_reports_an_upstream_refusal_as_a_client_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    directory = _directory(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError):
        await directory.list_logs(page=1, per_page=20)


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


CATEGORY_INDEXERS = [
    {
        "id": 1,
        "name": "Alpha",
        "capabilities": {
            "categories": [
                {
                    "id": 5000,
                    "name": "TV",
                    "subCategories": [{"id": 5030, "name": "TV/SD"}],
                }
            ]
        },
    },
    {
        "id": 2,
        "name": "Zeta",
        "capabilities": {
            "categories": [
                {"id": 2000, "name": "Movies", "subCategories": []},
                {"id": 5000, "name": "TV", "subCategories": []},
            ]
        },
    },
]


@pytest.mark.asyncio
async def test_list_categories_flattens_both_levels_across_every_indexer() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/indexer")
        return httpx.Response(200, json=CATEGORY_INDEXERS)

    directory = _directory(httpx.MockTransport(handler))
    categories = await directory.list_categories()

    # Deduplicated across indexers, sorted by id, subcategories included.
    assert [(category.category_id, category.name) for category in categories] == [
        (2000, "Movies"),
        (5000, "TV"),
        (5030, "TV/SD"),
    ]


@pytest.mark.asyncio
async def test_list_categories_ignores_an_indexer_that_advertises_none() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"id": 1, "name": "No capabilities"},
                {"id": 2, "name": "Empty", "capabilities": {}},
                {"id": 3, "name": "Nameless", "capabilities": {"categories": [{"id": 9}]}},
            ],
        )

    directory = _directory(httpx.MockTransport(handler))

    assert await directory.list_categories() == []


@pytest.mark.asyncio
async def test_list_categories_reports_an_upstream_refusal_as_a_client_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Unauthorized"})

    directory = _directory(httpx.MockTransport(handler))

    with pytest.raises(HttpClientError):
        await directory.list_categories()
