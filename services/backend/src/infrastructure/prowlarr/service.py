"""HTTP-based release search service powered by Prowlarr."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import httpx

from src.application.interfaces.releases import (
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchService,
    ReleaseSearchUnavailableError,
)
from src.infrastructure.http import BaseHttpClient, HttpClientError
from src.infrastructure.prowlarr.parsing import (
    safe_datetime,
    safe_int,
    safe_json,
    safe_str,
)


@dataclass(slots=True)
class ProwlarrReleaseSearchService(ReleaseSearchService):
    """Fetch release search results from the Prowlarr API."""

    base_url: str
    api_key: str
    timeout_seconds: float = 15.0
    categories: Sequence[int] | None = None
    _transport: httpx.AsyncBaseTransport | None = None
    _cache: dict[str, ReleaseSearchResultRecord] = field(default_factory=dict)
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

    async def search(
        self,
        query: str,
        request_id: str | None = None,
        indexer_id: int | None = None,
    ) -> ReleaseSearchResults:
        params: list[tuple[str, str]] = [("query", query), ("type", "search")]
        for category in self.categories or []:
            params.append(("categories", str(category)))
        if indexer_id is not None:
            params.append(("indexerIds", str(indexer_id)))

        # Retries are the caller's to decide: a per-indexer fan-out attempts
        # each indexer on its own schedule instead of inheriting the client's.
        try:
            response = await self._http.request("GET", "/search", params=params, retries=0)
        except HttpClientError as exc:
            raise ReleaseSearchUnavailableError(str(exc)) from exc

        if response.status_code == httpx.codes.BAD_REQUEST:
            payload = safe_json(response)
            if self._all_indexers_unavailable(payload):
                if indexer_id is not None:
                    # Scoped to one indexer, "all selected indexers" means that
                    # indexer itself is down, not that results are merely absent.
                    raise ReleaseSearchUnavailableError(
                        f"indexer {indexer_id} rejected the search: {payload}"
                    )
                return ReleaseSearchResults(results=[], query=query, total_results=0)
            self._raise_unavailable(response)

        self._raise_unavailable(response)
        payload = response.json()

        results: list[ReleaseSearchResultRecord] = []
        if not isinstance(payload, list):
            return ReleaseSearchResults(results=[], query=query, total_results=0)

        for item in payload:
            if not isinstance(item, dict):
                continue
            record = self._map_result(item, query, request_id)
            if record is not None:
                self._cache[record.release_id] = record
                results.append(record)

        results.sort(key=lambda result: (-(result.seeders or 0), result.release_name.lower()))
        return ReleaseSearchResults(results=results, query=query, total_results=len(results))

    def _raise_unavailable(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ReleaseSearchUnavailableError(str(exc)) from exc

    def _map_result(
        self,
        item: dict[str, object],
        query: str,
        request_id: str | None,
    ) -> ReleaseSearchResultRecord | None:
        title = safe_str(item.get("title"))
        guid = safe_str(item.get("guid"))
        if not title or not guid:
            return None

        size_bytes = safe_int(item.get("size"))
        size_text = self._format_size(size_bytes) if size_bytes is not None else "Unknown"
        magnet_url = safe_str(item.get("magnetUrl"))
        download_url = safe_str(item.get("downloadUrl"))
        if not magnet_url and not download_url:
            # Without either link we cannot offer a useful result.
            return None

        return ReleaseSearchResultRecord(
            release_id=guid,
            release_name=title,
            size=size_text,
            magnet_link=magnet_url,
            torrent_file_url=download_url,
            info_url=safe_str(item.get("infoUrl")),
            seeders=safe_int(item.get("seeders")),
            leechers=safe_int(item.get("leechers")),
            quality=safe_str(item.get("quality")),
            source=safe_str(item.get("indexer")),
            request_id=request_id,
            publish_date=safe_datetime(item.get("publishDate")),
            query=query,
        )

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 0:
            return "Unknown"
        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size_bytes} B"

    def _all_indexers_unavailable(self, payload: dict[str, object] | None) -> bool:
        if not payload:
            return False
        message = safe_str(payload.get("message"))
        unavailable = "all selected indexers" in message.lower() if message else False
        return unavailable

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._cache.get(release_id)

    async def fetch_torrent(self, url: str) -> bytes:
        response = await self._http.request("GET", url)
        response.raise_for_status()
        return response.content


__all__ = ["ProwlarrReleaseSearchService"]
