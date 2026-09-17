"""Prowlarr-backed view of the configured indexers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from src.application.interfaces.indexers import (
    IndexerDirectory,
    IndexerEventPage,
    IndexerEventRecord,
    IndexerLogPage,
    IndexerLogRecord,
    IndexerNotFoundError,
    IndexerRecord,
    IndexerTestResultRecord,
)
from src.core.logging import get_logger
from src.domain.enums import IndexerEventType, IndexerLogLevel, LogComponent
from src.infrastructure.http import BaseHttpClient, HttpClientError
from src.infrastructure.prowlarr.parsing import (
    safe_bool,
    safe_datetime,
    safe_int,
    safe_json,
    safe_json_list,
    safe_str,
)

# Prowlarr names its history event types in camel case, and answers a filter on
# either the name or the underlying number. Mapping both ways from one table
# keeps the request and the response reading the same vocabulary.
_EVENT_TYPES: dict[str, IndexerEventType] = {
    "unknown": IndexerEventType.UNKNOWN,
    "indexerQuery": IndexerEventType.INDEXER_QUERY,
    "indexerRss": IndexerEventType.INDEXER_RSS,
    "indexerAuth": IndexerEventType.INDEXER_AUTH,
    "indexerInfo": IndexerEventType.INDEXER_INFO,
    "releaseGrabbed": IndexerEventType.RELEASE_GRABBED,
}

_PROWLARR_EVENT_NAMES = {event: name for name, event in _EVENT_TYPES.items()}

_logger = get_logger(LogComponent.INTEGRATION_PROWLARR)

# Keys read onto the record itself, so the leftover data does not repeat them.
_LIFTED_DATA_KEYS = frozenset(
    {"query", "grabTitle", "title", "sourceTitle", "source", "elapsedTime"}
)

# Prowlarr lower-cases the level on the way out but compares the stored,
# capitalised value when filtering, so the filter cannot reuse our own value.
_PROWLARR_LEVEL_NAMES = {
    IndexerLogLevel.TRACE: "Trace",
    IndexerLogLevel.DEBUG: "Debug",
    IndexerLogLevel.INFO: "Info",
    IndexerLogLevel.WARN: "Warn",
    IndexerLogLevel.ERROR: "Error",
    IndexerLogLevel.FATAL: "Fatal",
}

# Prowlarr writes "warn", but has also written "warning" over the years.
_LEVEL_ALIASES = {"warning": IndexerLogLevel.WARN, "critical": IndexerLogLevel.FATAL}


@dataclass(slots=True)
class ProwlarrIndexerDirectory(IndexerDirectory):
    """Read indexer configuration and health from the Prowlarr API."""

    base_url: str
    api_key: str
    timeout_seconds: float = 15.0
    _transport: httpx.AsyncBaseTransport | None = None
    _http: BaseHttpClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._http = BaseHttpClient(
            base_url=self.base_url,
            headers={"X-Api-Key": self.api_key},
            timeout=self.timeout_seconds,
            transport=self._transport,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def list_indexers(self) -> list[IndexerRecord]:
        """Merge the indexer list with the failure log Prowlarr keeps separately.

        ``/indexerstatus`` only holds indexers Prowlarr is currently unhappy
        with, so an empty response means everything is healthy rather than
        unknown. The ``status`` field on the indexer list itself is not
        populated reliably, hence the second call.
        """

        indexers = safe_json_list(await self._get("/indexer"))
        statuses = self._statuses_by_indexer(safe_json_list(await self._get("/indexerstatus")))

        records: list[IndexerRecord] = []
        for item in indexers:
            if not isinstance(item, dict):
                continue
            record = self._map_indexer(item, statuses)
            if record is not None:
                records.append(record)

        records.sort(key=lambda record: record.name.lower())
        return records

    async def list_history(
        self,
        *,
        page: int,
        per_page: int,
        indexer_id: int | None = None,
        event_type: IndexerEventType | None = None,
    ) -> IndexerEventPage:
        """Read a page of Prowlarr's own indexer history.

        Prowlarr paginates and sorts this server-side, so the page is asked for
        rather than sliced out of a full list: the history runs to tens of
        thousands of rows on a busy instance.
        """

        params: list[tuple[str, str]] = [
            ("page", str(page)),
            ("pageSize", str(per_page)),
            ("sortKey", "date"),
            ("sortDirection", "descending"),
        ]
        if indexer_id is not None:
            params.append(("indexerIds", str(indexer_id)))
        if event_type is not None:
            params.append(("eventType", _PROWLARR_EVENT_NAMES[event_type]))

        response = await self._http.request("GET", "/history", params=params)
        self._raise_for_status(response)

        payload = safe_json(response) or {}
        records = payload.get("records")
        events: list[IndexerEventRecord] = []
        for item in records if isinstance(records, list) else []:
            if not isinstance(item, dict):
                continue
            record = self._map_event(item)
            if record is not None:
                events.append(record)

        total = safe_int(payload.get("totalRecords"))
        return IndexerEventPage(events=tuple(events), total=total if total is not None else 0)

    async def list_logs(
        self,
        *,
        page: int,
        per_page: int,
        min_level: IndexerLogLevel | None = None,
    ) -> IndexerLogPage:
        """Read a page of Prowlarr's own log, the one its UI shows as Events."""

        params: list[tuple[str, str]] = [
            ("page", str(page)),
            ("pageSize", str(per_page)),
            ("sortKey", "time"),
            ("sortDirection", "descending"),
        ]
        if min_level is not None:
            params.append(("level", _PROWLARR_LEVEL_NAMES[min_level]))

        response = await self._http.request("GET", "/log", params=params)
        self._raise_for_status(response)

        payload = safe_json(response) or {}
        records = payload.get("records")
        logs: list[IndexerLogRecord] = []
        for item in records if isinstance(records, list) else []:
            if not isinstance(item, dict):
                continue
            record = self._map_log(item)
            if record is not None:
                logs.append(record)

        total = safe_int(payload.get("totalRecords"))
        return IndexerLogPage(logs=tuple(logs), total=total if total is not None else 0)

    async def test_indexer(self, indexer_id: int) -> IndexerTestResultRecord:
        """Round-trip the stored definition back through Prowlarr's test.

        Prowlarr masks api keys and passwords as ``********`` when it hands out a
        definition and restores the stored value when it reads that sentinel
        back, so posting the definition unchanged tests it with real
        credentials.
        """

        definition = await self._get_indexer(indexer_id)
        name = safe_str(definition.get("name"))

        response = await self._http.request("POST", "/indexer/test", json=definition)
        if response.status_code == httpx.codes.BAD_REQUEST:
            return IndexerTestResultRecord(
                indexer_id=indexer_id,
                success=False,
                name=name,
                errors=self._validation_messages(safe_json_list(response)),
            )

        self._raise_for_status(response)
        return IndexerTestResultRecord(indexer_id=indexer_id, success=True, name=name)

    async def test_all_indexers(self) -> list[IndexerTestResultRecord]:
        """Test every enabled indexer.

        Prowlarr answers with 400 as soon as one indexer fails, carrying the same
        per-indexer body as a success, so the status code is a summary rather
        than an error.
        """

        response = await self._http.request("POST", "/indexer/testall")
        if response.status_code != httpx.codes.BAD_REQUEST:
            self._raise_for_status(response)

        names = {record.indexer_id: record.name for record in await self.list_indexers()}

        results: list[IndexerTestResultRecord] = []
        for item in safe_json_list(response):
            if not isinstance(item, dict):
                continue
            indexer_id = safe_int(item.get("id"))
            if indexer_id is None:
                continue
            errors = self._validation_messages(item.get("validationFailures"))
            results.append(
                IndexerTestResultRecord(
                    indexer_id=indexer_id,
                    success=not errors,
                    name=names.get(indexer_id),
                    errors=errors,
                )
            )

        failed = [result.name or str(result.indexer_id) for result in results if not result.success]
        if failed:
            _logger.warning("Indexer tests failed", failed=failed)
        return results

    async def _get(self, path: str) -> httpx.Response:
        response = await self._http.request("GET", path)
        self._raise_for_status(response)
        return response

    async def _get_indexer(self, indexer_id: int) -> dict[str, Any]:
        response = await self._http.request("GET", f"/indexer/{indexer_id}")
        if response.status_code == httpx.codes.NOT_FOUND:
            raise IndexerNotFoundError(f"Prowlarr has no indexer {indexer_id}")

        self._raise_for_status(response)
        try:
            payload = response.json()
        except ValueError as exc:
            raise HttpClientError(f"Prowlarr returned an unreadable indexer {indexer_id}") from exc
        if not isinstance(payload, dict):
            raise HttpClientError(f"Prowlarr returned an unreadable indexer {indexer_id}")
        return payload

    def _statuses_by_indexer(self, payload: list[object]) -> dict[int, dict[str, object]]:
        statuses: dict[int, dict[str, object]] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            indexer_id = safe_int(item.get("indexerId"))
            if indexer_id is not None:
                statuses[indexer_id] = item
        return statuses

    def _map_indexer(
        self,
        item: dict[str, object],
        statuses: dict[int, dict[str, object]],
    ) -> IndexerRecord | None:
        indexer_id = safe_int(item.get("id"))
        name = safe_str(item.get("name"))
        if indexer_id is None or name is None:
            return None

        status = statuses.get(indexer_id, {})
        return IndexerRecord(
            indexer_id=indexer_id,
            name=name,
            enabled=safe_bool(item.get("enable")),
            protocol=safe_str(item.get("protocol")),
            privacy=safe_str(item.get("privacy")),
            priority=safe_int(item.get("priority")),
            supports_search=safe_bool(item.get("supportsSearch")),
            supports_rss=safe_bool(item.get("supportsRss")),
            indexer_urls=self._urls(item.get("indexerUrls")),
            disabled_till=safe_datetime(status.get("disabledTill")),
            most_recent_failure=safe_datetime(status.get("mostRecentFailure")),
            initial_failure=safe_datetime(status.get("initialFailure")),
        )

    def _map_event(self, item: dict[str, object]) -> IndexerEventRecord | None:
        event_id = safe_int(item.get("id"))
        indexer_id = safe_int(item.get("indexerId"))
        occurred_at = safe_datetime(item.get("date"))
        if event_id is None or indexer_id is None or occurred_at is None:
            return None

        data = self._event_data(item.get("data"))
        return IndexerEventRecord(
            event_id=event_id,
            indexer_id=indexer_id,
            occurred_at=occurred_at,
            event_type=self._event_type(item.get("eventType")),
            successful=safe_bool(item.get("successful"), default=True),
            indexer_name=safe_str(item.get("indexerName")),
            query=safe_str(data.get("query")),
            title=safe_str(data.get("grabTitle") or data.get("title"))
            or safe_str(item.get("sourceTitle")),
            source=safe_str(data.get("source")),
            elapsed_ms=safe_int(data.get("elapsedTime")),
            data={
                key: value
                for key, raw in data.items()
                if key not in _LIFTED_DATA_KEYS and (value := safe_str(raw)) is not None
            },
        )

    def _event_type(self, value: object) -> IndexerEventType:
        """Read Prowlarr's event type, falling back to unknown.

        Prowlarr adds members to this enum between releases, and an event nobody
        here has a name for is still worth listing.
        """

        name = safe_str(value)
        if name is None:
            return IndexerEventType.UNKNOWN
        for candidate, event in _EVENT_TYPES.items():
            if candidate.lower() == name.lower():
                return event
        return IndexerEventType.UNKNOWN

    def _map_log(self, item: dict[str, object]) -> IndexerLogRecord | None:
        log_id = safe_int(item.get("id"))
        occurred_at = safe_datetime(item.get("time"))
        if log_id is None or occurred_at is None:
            return None

        # An exception with no message of its own is the whole entry; dropping it
        # would lose the failures worth reading this log for.
        message = safe_str(item.get("message"))
        exception = safe_str(item.get("exception"))
        exception_type = safe_str(item.get("exceptionType"))
        if message is None:
            message = exception_type or ""

        return IndexerLogRecord(
            log_id=log_id,
            occurred_at=occurred_at,
            level=self._log_level(item.get("level")),
            message=message,
            component=safe_str(item.get("logger")),
            method=safe_str(item.get("method")),
            exception=exception,
            exception_type=exception_type,
        )

    def _log_level(self, value: object) -> IndexerLogLevel:
        name = safe_str(value)
        if name is None:
            return IndexerLogLevel.INFO
        lowered = name.lower()
        for level in IndexerLogLevel:
            if level.value == lowered:
                return level
        return _LEVEL_ALIASES.get(lowered, IndexerLogLevel.INFO)

    def _event_data(self, value: object) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        return {str(key): item for key, item in value.items()}

    def _urls(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        urls = (safe_str(entry) for entry in value)
        return tuple(url for url in urls if url is not None)

    def _validation_messages(self, value: object) -> tuple[str, ...]:
        if not isinstance(value, list):
            return ()
        messages: list[str] = []
        for entry in value:
            if not isinstance(entry, dict):
                continue
            message = safe_str(entry.get("errorMessage"))
            if message is not None:
                messages.append(message)
        return tuple(messages)

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Report an upstream refusal as a client error rather than our crash."""

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HttpClientError(
                f"Prowlarr rejected {response.request.method} {response.request.url.path} "
                f"with {response.status_code}"
            ) from exc


__all__ = ["ProwlarrIndexerDirectory"]
