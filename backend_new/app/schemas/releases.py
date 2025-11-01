from pydantic import BaseModel, ConfigDict

from pydantic import BaseModel

from app.schemas.common import Release, ReleaseStats


class UpdateFileMapping(BaseModel):
    episode_mapping: dict | None = None
    request_mapping: dict | None = None


class SuccessResponse(BaseModel):
    success: bool = True


class ReleaseCollection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    releases: list[Release]


class NewRelease(BaseModel):
    magnet_link: str | None = None
    request_ids: list[int]
    name: str | None = None
    size: int | None = 0
    torrent_source: str | None = None
    quality: str | None = None
