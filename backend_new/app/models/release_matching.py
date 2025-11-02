from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReleaseFileMatching(Base):
    __tablename__ = "release_file_matchings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id", ondelete="CASCADE"))
    show_id: Mapped[int | None] = mapped_column(ForeignKey("shows.id", ondelete="SET NULL"))
    file_name: Mapped[str] = mapped_column(String(1024))
    season_number: Mapped[int | None] = mapped_column(Integer)
    episode_number: Mapped[int | None] = mapped_column(Integer)

    release: Mapped["Release"] = relationship("Release", back_populates="file_matchings")
    show: Mapped["Show | None"] = relationship("Show")


if TYPE_CHECKING:  # pragma: no cover
    from app.models.release import Release
    from app.models.show import Show
