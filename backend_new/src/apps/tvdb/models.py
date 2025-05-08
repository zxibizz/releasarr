from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.apps.tvdb.schemas import TvdbShowData
from src.db import Base
from src.db.types import PydanticType


class TVDBSeries(Base):
    __tablename__ = "tvdb_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tvdb_series_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    data: Mapped[TvdbShowData] = mapped_column(
        PydanticType(TvdbShowData), nullable=False
    )
