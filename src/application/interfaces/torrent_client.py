from typing import Protocol


class I_TorrentClient(Protocol):
    async def add_torrent(self, raw_torrent: bytes) -> None: ...

    async def torrent_properties(self, hash: str) -> dict: ...
