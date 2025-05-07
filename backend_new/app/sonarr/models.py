from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db import Base
from app.prowlarr.models import ProwlarrRelease
from app.sonarr.schemas import SonarrEpisode
from app.torrent.models import Torrent

T = TypeVar("T", bound=BaseModel)


class PydanticType(TypeDecorator, Generic[T]):
    """SQLAlchemy type for storing Pydantic models in a database.

    This type can handle both single Pydantic models and lists of Pydantic models.

    Usage:
        # For a single Pydantic model
        field: Mapped[MyModel] = mapped_column(PydanticType(MyModel))

        # For a list of Pydantic models
        field: Mapped[List[MyModel]] = mapped_column(PydanticType(List[MyModel]))
    """

    impl = JSONB
    cache_ok = True

    def __init__(self, python_type: Type[T], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.python_type = python_type

        # Check if the type is a List[T]
        origin = get_origin(python_type)
        if origin is list or origin is List:
            self.is_list = True
            self.item_type = get_args(python_type)[0]
        else:
            self.is_list = False
            self.item_type = python_type

    def process_bind_param(self, value: Optional[Union[T, List[T]]], dialect):
        if value is None:
            return None

        if self.is_list:
            return [item.model_dump() for item in value]
        else:
            return value.model_dump()

    def process_result_value(self, value: Any, dialect):
        if value is None:
            return None

        if self.is_list:
            return [self.item_type.model_validate(item) for item in value]
        else:
            return self.item_type.model_validate(value)


class TVDBSeries(Base):
    __tablename__ = "tvdb_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tvdb_series_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)


class SonarrRequest(Base):
    __tablename__ = "sonarr_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sonarr_series_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tvdb_series_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    is_missing: Mapped[bool] = mapped_column(Boolean, default=False)

    episodes: Mapped[List[SonarrEpisode]] = mapped_column(
        PydanticType(List[SonarrEpisode]), nullable=False
    )

    prowlarr_manual_search_string: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )

    prowlarr_release_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("prowlarr_releases.id"), nullable=True
    )
    prowlarr_release: Mapped[Optional[ProwlarrRelease]] = relationship(
        "ProwlarrRelease"
    )

    torrent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("torrents.id"), nullable=True
    )
    torrent: Mapped[Optional[Torrent]] = relationship("Torrent")

    torrent_files_matching: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSONB, nullable=True
    )

    last_imported_torrent_guid: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
