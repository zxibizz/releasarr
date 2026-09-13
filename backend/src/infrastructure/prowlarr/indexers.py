"""Prowlarr-backed view of the configured indexers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from src.application.interfaces.indexers import (
    IndexerDirectory,
    IndexerNotFoundError,
    IndexerRecord,
    IndexerTestResultRecord,
)
from src.infrastructure.http import BaseHttpClient, HttpClientError
from src.infrastructure.prowlarr.parsing import (
    safe_bool,
    safe_datetime,
    safe_int,
    safe_json_list,
    safe_str,
)


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
