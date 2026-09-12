"""HTTP-based release search service powered by Prowlarr."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from src.application.interfaces.releases import (
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchService,
)
from src.infrastructure.http import BaseHttpClient


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

    async def aclose(self) -> None:
        await self._http.aclose()

    async def search(self, query: str, request_id: str | None = None) -> ReleaseSearchResults:
        params: list[tuple[str, str]] = [("query", query), ("type", "search")]
        for category in self.categories or []:
            params.append(("categories", str(category)))

        response = await self._http.request("GET", "/search", params=params)

        if response.status_code == httpx.codes.BAD_REQUEST:
            payload = self._safe_json(response)
            if self._all_indexers_unavailable(payload):
                return ReleaseSearchResults(results=[], query=query, total_results=0)
            response.raise_for_status()

        response.raise_for_status()
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

    def _map_result(
        self,
        item: dict[str, object],
        query: str,
        request_id: str | None,
    ) -> ReleaseSearchResultRecord | None:
        title = self._safe_str(item.get("title"))
        guid = self._safe_str(item.get("guid"))
        if not title or not guid:
            return None

        size_bytes = self._safe_int(item.get("size"))
        size_text = self._format_size(size_bytes) if size_bytes is not None else "Unknown"
        magnet_url = self._safe_str(item.get("magnetUrl"))
        download_url = self._safe_str(item.get("downloadUrl"))
        if not magnet_url and not download_url:
            # Without either link we cannot offer a useful result.
            return None

        return ReleaseSearchResultRecord(
            release_id=guid,
            release_name=title,
            size=size_text,
            magnet_link=magnet_url,
            torrent_file_url=download_url,
            info_url=self._safe_str(item.get("infoUrl")),
            seeders=self._safe_int(item.get("seeders")),
            leechers=self._safe_int(item.get("leechers")),
            quality=self._safe_str(item.get("quality")),
            source=self._safe_str(item.get("indexer")),
            request_id=request_id,
            publish_date=self._safe_datetime(item.get("publishDate")),
        )

    def _safe_str(self, value: object) -> str | None:
        if value is None:
            return None
        result = str(value).strip()
        return result or None

    def _safe_datetime(self, value: object) -> datetime | None:
        text = self._safe_str(value)
        if text is None:
            return None
        # Prowlarr sends ISO-8601, commonly with a trailing "Z" that
        # fromisoformat only accepts from Python 3.11 onwards.
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    def _safe_int(self, value: object) -> int | None:
        if not isinstance(value, int | float | str):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

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

    def _safe_json(self, response: httpx.Response) -> dict[str, object] | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        if isinstance(payload, dict):
            return payload
        return None

    def _all_indexers_unavailable(self, payload: dict[str, object] | None) -> bool:
        if not payload:
            return False
        message = self._safe_str(payload.get("message"))
        unavailable = "all selected indexers" in message.lower() if message else False
        return unavailable

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._cache.get(release_id)

    async def fetch_torrent(self, url: str) -> bytes:
        response = await self._http.request("GET", url)
        response.raise_for_status()
        return response.content


__all__ = ["ProwlarrReleaseSearchService"]
