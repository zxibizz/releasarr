from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.request import MediaRequest
    from app.models.release_file import ReleaseFile


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    hash: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    download_speed: Mapped[int] = mapped_column(Integer, default=0)
    upload_speed: Mapped[int] = mapped_column(Integer, default=0)
    seeders: Mapped[int] = mapped_column(Integer, default=0)
    leechers: Mapped[int] = mapped_column(Integer, default=0)
    ratio: Mapped[float] = mapped_column(Float, default=0.0)
    added_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    torrent_source: Mapped[str | None] = mapped_column(String(128))
    quality: Mapped[str | None] = mapped_column(String(64))

    requests: Mapped[list["MediaRequest"]] = relationship(
        "MediaRequest", secondary="release_requests", back_populates="releases"
    )
    files: Mapped[list["ReleaseFile"]] = relationship(
        "ReleaseFile", back_populates="release", cascade="all, delete-orphan"
    )


class ReleaseStatsAggregate(Base):
    __tablename__ = "release_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    total_releases: Mapped[int] = mapped_column(Integer, default=0)
    active_downloads: Mapped[int] = mapped_column(Integer, default=0)
    completed_releases: Mapped[int] = mapped_column(Integer, default=0)
    total_size: Mapped[int] = mapped_column(BigInteger, default=0)
    total_uploaded: Mapped[int] = mapped_column(BigInteger, default=0)
    total_downloaded: Mapped[int] = mapped_column(BigInteger, default=0)
