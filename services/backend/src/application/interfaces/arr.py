"""Interfaces shared by the Sonarr and Radarr services.

Both apps expose the same library-management resources under the same shapes, so
the root folder and quality profile records live here rather than being spelled
out twice.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ArrRootFolder:
    """A library location configured in Sonarr or Radarr."""

    path: str
    free_space: int | None = None
    accessible: bool = True


@dataclass(slots=True)
class ArrQualityProfile:
    """A quality profile configured in Sonarr or Radarr."""

    id: int
    name: str


__all__ = ["ArrQualityProfile", "ArrRootFolder"]
