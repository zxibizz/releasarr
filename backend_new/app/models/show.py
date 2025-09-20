from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.release import Release


class Show(Base):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sonarr_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    tvdb_id: Mapped[int | None] = mapped_column(Integer)

    sonarr_data: Mapped[dict | None] = mapped_column(JSON)
    tvdb_data: Mapped[dict | None] = mapped_column(JSON)
    prowlarr_data: Mapped[dict | None] = mapped_column(JSON)

    prowlarr_search: Mapped[str | None] = mapped_column(String(255))
    is_missing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missing_seasons: Mapped[list[int] | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    releases: Mapped[list["Release"]] = relationship(
        "Release", back_populates="show", cascade="all, delete-orphan"
    )
