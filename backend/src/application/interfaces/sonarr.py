"""Interfaces for interacting with Sonarr services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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


__all__ = [
    "ManualImportFile",
    "MissingSeriesRecord",
    "SeriesDetails",
    "SeriesSeasonDetails",
    "SonarrEpisode",
    "SonarrService",
]
