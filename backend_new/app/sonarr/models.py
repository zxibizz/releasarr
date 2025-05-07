from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, PydanticType
from app.prowlarr.models import ProwlarrRelease
from app.sonarr.schemas import SonarrEpisode
from app.torrent.models import Torrent


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
