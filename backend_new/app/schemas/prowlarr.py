from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TorrentFile(BaseModel):
    name: str
    length: int


class TorrentMeta(BaseModel):
    name: str
    info_hash: str
    total_size: int
    creation_date: datetime | None = None
    files: list[TorrentFile] = []


class ReleaseData(BaseModel):
    guid: str
    age: int | None = None
    grabs: int | None = None
    info_url: str | None = None
    size: int | None = None
    title: str
    indexer: str | None = None
    indexer_id: int | None = None
    seeders: int | None = None
    leechers: int | None = None
    download_url: str
    pk: str | None = None
