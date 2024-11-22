from typing import Optional, Protocol

from src.application.schemas import ReleaseData, TorrentMeta


class SearchError(Exception): ...


class NoIndexerAvailableError(SearchError): ...


class I_ReleaseSearcher(Protocol):
    async def search(
        self, search_string: str, indexer_ids: Optional[list[int]] = None
    ) -> list[ReleaseData]: ...

    async def get_torrent(self, download_url: str) -> tuple[TorrentMeta, bytes]: ...
