from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.request import MediaRequest
    from app.models.release_file import ReleaseFile
    from app.models.release_matching import ReleaseFileMatching
    from app.models.show import Show


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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    torrent_source: Mapped[str | None] = mapped_column(String(128))
    quality: Mapped[str | None] = mapped_column(String(64))
    search: Mapped[str | None] = mapped_column(String(255))
    prowlarr_guid: Mapped[str | None] = mapped_column(String(255))
    prowlarr_data: Mapped[dict | None] = mapped_column(JSON)
    qbittorrent_guid: Mapped[str | None] = mapped_column(String(128))
    qbittorrent_data: Mapped[dict | None] = mapped_column(JSON)
    torrent_stats: Mapped[dict | None] = mapped_column(JSON)
    torrent_is_finished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_imported_files_hash: Mapped[str | None] = mapped_column(String(128))
    last_exported_torrent_guid: Mapped[str | None] = mapped_column(String(128))
    export_failures_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id", ondelete="SET NULL"))

    requests: Mapped[list["MediaRequest"]] = relationship(
        "MediaRequest", secondary="release_requests", back_populates="releases"
    )
    files: Mapped[list["ReleaseFile"]] = relationship(
        "ReleaseFile", back_populates="release", cascade="all, delete-orphan"
    )
    file_matchings: Mapped[list["ReleaseFileMatching"]] = relationship(
        "ReleaseFileMatching", back_populates="release", cascade="all, delete-orphan"
    )
    show: Mapped["Show | None"] = relationship("Show", back_populates="releases")

