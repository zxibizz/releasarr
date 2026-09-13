"""Interfaces for interacting with Sonarr services."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder


@dataclass(slots=True)
class MissingSeriesRecord:
    """Minimal data describing missing Sonarr seasons."""

    series_id: int
    title: str
    season_numbers: list[int]
    tvdb_id: int | None
    imdb_id: str | None


@dataclass(slots=True)
class SeriesSeasonDetails:
    """Detailed information about a Sonarr season."""

    season_number: int
    episode_count: int
    total_episode_count: int
    episode_file_count: int
    monitored: bool = False


@dataclass(slots=True)
class SeriesDetails:
    """Detailed information about a Sonarr series."""

    id: int
    title: str
    year: int | None
    overview: str | None
    poster_url: str | None
    imdb_id: str | None
    tvdb_id: int | None
    genres: list[str]
    seasons: dict[int, SeriesSeasonDetails]
    # Whether Sonarr monitors seasons that appear after the series was added.
    monitor_new_seasons: bool = False


@dataclass(slots=True)
class ManualImportFile:
    """File details for Sonarr manual import command."""

    path: str
    series_id: int
    episode_ids: list[int]
    folder_name: str


@dataclass(slots=True)
class SonarrEpisode:
    """Minimal details for a Sonarr episode."""

    id: int
    season_number: int
    episode_number: int
    title: str = ""
    # Absent for an episode Sonarr has no date for, which is both an episode
    # announced without one and one whose season is yet to be scheduled.
    air_date: datetime | None = None
    has_file: bool = False
    # Bytes on disk, for an episode Sonarr holds a file for.
    file_size: int | None = None


@dataclass(slots=True)
class SeriesLookup:
    """A series as Sonarr's lookup reports it, in or out of the library.

    ``existing_series_id`` is how the lookup marks a series that is already in
    the library: Sonarr fills the field in for those and leaves it at zero for
    everything else.
    """

    tvdb_id: int
    title: str
    year: int | None = None
    existing_series_id: int | None = None
    season_numbers: list[int] = field(default_factory=list)
    monitored_seasons: list[int] = field(default_factory=list)


class SonarrService(Protocol):
    """Protocol describing the subset of Sonarr operations we rely on."""

    async def get_missing_series(self) -> list[MissingSeriesRecord]:
        """Return Sonarr series with missing monitored episodes grouped by season."""

    async def get_series(self, series_id: int) -> SeriesDetails:
        """Return detailed information for a single Sonarr series."""

    async def get_episodes(self, series_id: int) -> list[SonarrEpisode]:
        """Return all episodes for a series."""

    async def manual_import(self, files: list[ManualImportFile]) -> bool:
        """Trigger a manual import command for the designated files."""

    async def get_root_folders(self) -> list[ArrRootFolder]:
        """Return the library locations configured in Sonarr."""

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        """Return the quality profiles configured in Sonarr."""

    async def search_series(self, term: str) -> list[SeriesLookup]:
        """Return series matching a free-text term."""

    async def lookup_series(self, tvdb_id: int) -> SeriesLookup | None:
        """Return the series matching a TVDB id, or None when TVDB has no such series."""

    async def add_series(
        self,
        *,
        tvdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
        monitored_seasons: Sequence[int],
        monitor_new_seasons: bool = False,
    ) -> int:
        """Add a series to the library and return its Sonarr id."""

    async def apply_season_monitoring(
        self,
        series_id: int,
        *,
        monitor: Sequence[int] = (),
        unmonitor: Sequence[int] = (),
        monitor_new_seasons: bool | None = None,
    ) -> None:
        """Change the monitoring of the named seasons of a series in the library.

        Only the seasons named are touched, so a season monitored outside
        releasarr keeps whatever the user chose for it. The series itself is
        always left monitored, releasarr keeping no switch of its own for it.
        """

    async def wait_for_series_episodes(
        self,
        series_id: int,
        season_numbers: Sequence[int],
        timeout_seconds: float | None = None,
    ) -> SeriesDetails:
        """Wait until Sonarr has populated episodes for the given seasons."""


__all__ = [
    "ManualImportFile",
    "MissingSeriesRecord",
    "SeriesDetails",
    "SeriesLookup",
    "SeriesSeasonDetails",
    "SonarrEpisode",
    "SonarrService",
]
