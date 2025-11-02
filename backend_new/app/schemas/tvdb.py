from __future__ import annotations

from pydantic import BaseModel


class TvdbShowData(BaseModel):
    id: int
    year: int | None = None
    genres: list[str] = []
    country: str | None = None
    title: str
    title_en: str | None = None
    image_url: str | None = None
    overview: str | None = None
