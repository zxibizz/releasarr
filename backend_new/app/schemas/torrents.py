from pydantic import BaseModel, ConfigDict


class TorrentResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    size: str
    link: str
    seeders: int
    leechers: int
    quality: str
    source: str


class TorrentSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    results: list[TorrentResult]
    query: str
    total_results: int


class DownloadTorrentRequest(BaseModel):
    torrent_link: str
    request_id: int
