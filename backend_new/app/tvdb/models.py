from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, PydanticType
from app.tvdb.schemas import TvdbShowData


class TVDBSeries(Base):
    __tablename__ = "tvdb_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tvdb_series_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    data: Mapped[TvdbShowData] = mapped_column(
        PydanticType(TvdbShowData), nullable=False
    )
