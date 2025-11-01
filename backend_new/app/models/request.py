from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.release import Release


class RequestType(str, Enum):
    MOVIE = "movie"
    SERIES = "series"


class RequestStatus(str, Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


release_request_table = Table(
    "release_requests",
    Base.metadata,
    Column("release_id", ForeignKey("releases.id"), primary_key=True),
    Column("request_id", ForeignKey("requests.id"), primary_key=True),
)


class MediaRequest(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    type: Mapped[RequestType] = mapped_column(SAEnum(RequestType), nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        SAEnum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int | None]
    poster_url: Mapped[str | None] = mapped_column(String(500))
    overview: Mapped[str | None]
    genres: Mapped[str | None]
    imdb_id: Mapped[str | None] = mapped_column(String(64))

    runtime: Mapped[int | None]
    season_number: Mapped[int | None]
    total_episodes: Mapped[int | None]
    series_title: Mapped[str | None] = mapped_column(String(255))
    series_year: Mapped[int | None]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    releases: Mapped[list["Release"]] = relationship(
        "Release", secondary=release_request_table, back_populates="requests"
    )

    def as_genre_list(self) -> list[str]:
        if not self.genres:
            return []
        return [genre.strip() for genre in self.genres.split(",") if genre.strip()]

    def set_genre_list(self, genres: list[str]) -> None:
        self.genres = ",".join(genres)
