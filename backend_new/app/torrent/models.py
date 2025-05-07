from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Torrent(Base):
    __tablename__ = "torrents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guid: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
