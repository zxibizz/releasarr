from typing import Optional

from pydantic import BaseModel


class ProwlarrReleaseSchema(BaseModel):
    id: Optional[int] = None
    search_string: Optional[str] = None
    title: Optional[str] = None
    info_url: Optional[str] = None
    size: Optional[int] = None

    class Config:
        from_attributes = True
