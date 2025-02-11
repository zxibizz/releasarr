from datetime import datetime

from pydantic import BaseModel


class ReleaseData(BaseModel):
    guid: str
    age: int
    grabs: int
    info_url: str
    size: int
    title: str
    indexer: str
    indexer_id: int
    seeders: int
    leechers: int
    download_url: str

    @property
    def pk(self):
        if not self.indexer.lower().startswith("anilibria"):
            return self.info_url

        if "x264" in self.title:
            return f"{self.info_url}:x264"
        if "x265" in self.title:
            return f"{self.info_url}:x265"
        raise ValueError


class TorrentMeta(BaseModel):
    name: str
    info_hash: str
    total_size: int
    creation_date: datetime
    files: list["TorrentFile"]


class TorrentFile(BaseModel):
    name: str
    length: int
