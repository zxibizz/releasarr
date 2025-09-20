from __future__ import annotations

from loguru import logger

from app.clients.factory import get_clients
from app.schemas.torrents import TorrentResult, TorrentSearchResponse


class TorrentService:
    def __init__(self) -> None:
        self.clients = get_clients()

    async def search(self, query: str) -> TorrentSearchResponse:
        if not query.strip():
            return TorrentSearchResponse(results=[], query=query, total_results=0)
        if not self.clients.prowlarr.enabled:
            logger.debug("Prowlarr disabled; returning empty search result")
            return TorrentSearchResponse(results=[], query=query, total_results=0)

        releases = await self.clients.prowlarr.search(query)
        results: list[TorrentResult] = []
        for item in releases:
            if not item.get("downloadUrl"):
                continue
            quality_info = item.get("quality")
            if isinstance(quality_info, dict):
                nested_quality = quality_info.get("quality")
                if isinstance(nested_quality, dict):
                    quality_name = nested_quality.get("name", "Unknown")
                else:
                    quality_name = quality_info.get("name", "Unknown")
            else:
                quality_name = quality_info or "Unknown"

            results.append(
                TorrentResult(
                    id=item.get("guid") or str(item.get("id")),
                    name=item.get("title"),
                    size=str(item.get("size")),
                    link=item.get("downloadUrl"),
                    seeders=item.get("seeders", 0),
                    leechers=item.get("leechers", 0),
                    quality=quality_name,
                    source=item.get("indexer"),
                )
            )
        return TorrentSearchResponse(
            results=results,
            query=query,
            total_results=len(results),
        )
