from typing import List, Optional

from pydantic import BaseModel


class TvdbShowData(BaseModel):
    id: int
    year: int
    genres: List[str]
    country: str
    title: str
    title_en: Optional[str] = None
    image_url: Optional[str] = None
    overview: str


class TvdbSearchResult(BaseModel):
    id: int
    type: str
    year: Optional[int] = None
    genres: List[str] = []
    country: Optional[str] = None
    title: str
    title_eng: Optional[str] = None
    title_rus: Optional[str] = None
    image_url: Optional[str] = None
    overview: Optional[str] = None
    overview_eng: Optional[str] = None
    overview_rus: Optional[str] = None
