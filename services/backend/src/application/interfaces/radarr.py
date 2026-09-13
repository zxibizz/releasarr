"""Interfaces for interacting with Radarr services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from src.application.interfaces.arr import ArrQualityProfile, ArrRootFolder


@dataclass(slots=True)
class MovieDetails:
    """Detailed information about a Radarr movie."""

    id: int
    title: str
    year: int | None
    overview: str | None
    poster_url: str | None
    imdb_id: str | None
    tmdb_id: int | None
    genres: list[str] = field(default_factory=list)
    runtime_minutes: int | None = None
    has_file: bool = False


@dataclass(slots=True)
class MovieImportFile:
    """File details for Radarr's manual import command."""

    path: str
    movie_id: int
    folder_name: str


@dataclass(slots=True)
class MovieLookup:
    """A movie as Radarr's lookup reports it, in or out of the library.

    ``existing_movie_id`` is how the lookup marks a movie that is already in the
    library: Radarr fills the field in for those and leaves it at zero for
    everything else.
    """

    tmdb_id: int
    title: str
    year: int | None = None
    existing_movie_id: int | None = None


class RadarrService(Protocol):
    """Protocol describing the subset of Radarr operations we rely on."""

    async def get_missing_movies(self) -> list[MovieDetails]:
        """Return monitored Radarr movies that are still missing a file."""

    async def get_movie(self, movie_id: int) -> MovieDetails:
        """Return detailed information for a single Radarr movie."""

    async def manual_import(self, files: list[MovieImportFile]) -> bool:
        """Trigger a manual import command for the designated files."""

    async def get_root_folders(self) -> list[ArrRootFolder]:
        """Return the library locations configured in Radarr."""

    async def get_quality_profiles(self) -> list[ArrQualityProfile]:
        """Return the quality profiles configured in Radarr."""

    async def search_movies(self, term: str) -> list[MovieLookup]:
        """Return movies matching a free-text term."""

    async def lookup_movie(self, tmdb_id: int) -> MovieLookup | None:
        """Return the movie matching a TMDB id, or None when TMDB has no such movie."""

    async def add_movie(
        self,
        *,
        tmdb_id: int,
        root_folder_path: str,
        quality_profile_id: int,
    ) -> int:
        """Add a movie to the library and return its Radarr id."""

    async def set_movie_monitored(self, movie_id: int, *, monitored: bool = True) -> None:
        """Set whether Radarr monitors a movie already in the library."""


__all__ = [
    "MovieDetails",
    "MovieImportFile",
    "MovieLookup",
    "RadarrService",
]
