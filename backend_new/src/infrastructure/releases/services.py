"""Stubbed release service adapters used until real integrations arrive."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.application.interfaces.releases import (
    QueuedDownload,
    ReleaseDownloadService,
    ReleaseLifecycleService,
    ReleaseSearchResultRecord,
    ReleaseSearchResults,
    ReleaseSearchService,
)


@dataclass(slots=True)
class InMemoryReleaseLifecycleService(ReleaseLifecycleService):
    """Simple stateful lifecycle service toggling paused releases in memory."""

    paused_releases: set[str] = field(default_factory=set)

    async def pause(self, release_id: str) -> bool:
        if release_id in self.paused_releases:
            return False
        self.paused_releases.add(release_id)
        return True

    async def resume(self, release_id: str) -> bool:
        if release_id not in self.paused_releases:
            return False
        self.paused_releases.remove(release_id)
        return True


@dataclass(slots=True)
class InMemoryReleaseSearchService(ReleaseSearchService):
    """Search service returning pre-registered results per query."""

    _registry: dict[tuple[str, str | None], list[ReleaseSearchResultRecord]] = field(
        default_factory=dict,
    )
    _cache: dict[str, ReleaseSearchResultRecord] = field(default_factory=dict)
    _torrents: dict[str, bytes] = field(default_factory=dict)

    def register_results(
        self,
        query: str,
        *,
        request_id: str | None,
        results: list[ReleaseSearchResultRecord],
    ) -> None:
        self._registry[(query, request_id)] = list(results)
        for result in results:
            self._cache[result.release_id] = result

    async def search(self, query: str, request_id: str | None = None) -> ReleaseSearchResults:
        key = (query, request_id)
        matches = self._registry.get(key, [])
        return ReleaseSearchResults(results=list(matches), query=query, total_results=len(matches))

    def resolve(self, release_id: str) -> ReleaseSearchResultRecord | None:
        return self._cache.get(release_id)

    def register_torrent(self, release_id: str, data: bytes) -> None:
        self._torrents[release_id] = data

    async def fetch_torrent(self, url: str) -> bytes:
        if url.startswith("memory://"):
            release_id = url.removeprefix("memory://")
            if release_id in self._torrents:
                return self._torrents[release_id]
        raise FileNotFoundError(f"Torrent data not registered for URL '{url}'")


@dataclass(slots=True)
class InMemoryReleaseDownloadService(ReleaseDownloadService):
    """Download service queuing releases and tracking requested operations."""

    queued: list[tuple[str, str]] = field(default_factory=list)

    async def queue_download(self, request_id: str, release_id: str) -> QueuedDownload:
        self.queued.append((request_id, release_id))
        operation_id = f"queue:{request_id}:{release_id}"
        location = f"/operations/{operation_id}"
        return QueuedDownload(
            operation="queue_download",
            status="accepted",
            operation_id=operation_id,
            location=location,
            message=None,
            resource_id=release_id,
            details={"request_id": request_id, "release_id": release_id},
        )


__all__ = [
    "InMemoryReleaseDownloadService",
    "InMemoryReleaseLifecycleService",
    "InMemoryReleaseSearchService",
]
