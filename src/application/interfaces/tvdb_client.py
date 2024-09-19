from typing import Protocol

from pydantic import BaseModel


class TvdbShowData(BaseModel):
    id: int
    year: int
    genres: list
    country: str
    title: str
    title_en: str
    image_url: str | None
    overview: str


class I_TvdbClient(Protocol):
    async def get_series(self, tvdb_id: str) -> TvdbShowData: ...
