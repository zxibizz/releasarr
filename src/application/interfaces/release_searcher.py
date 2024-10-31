from typing import Protocol

from src.application.schemas import ReleaseData, TorrentMeta


class I_ReleaseSearcher(Protocol):
    async def search(self, search_string) -> list[ReleaseData]: ...

    async def get_torrent(self, download_url) -> tuple[TorrentMeta, bytes]: ...
