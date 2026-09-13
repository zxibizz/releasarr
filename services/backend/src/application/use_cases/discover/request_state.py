"""Lookups telling the add-request flow what has already been requested.

Requests are keyed by the Sonarr/Radarr identifier rather than the TVDB/TMDB
one, so the library id a lookup reports is what joins them to a search hit. Both
helpers read the whole set in one query instead of asking per result: the table
only ever holds this installation's own requests, and a search answers for a
page of them at a time.
"""

from __future__ import annotations

from src.application.interfaces.media_requests import (
    MediaRequestRecord,
    MediaRequestRepository,
)


async def requested_seasons_by_series(
    repository: MediaRequestRepository,
) -> dict[int, dict[int, str]]:
    """Map each Sonarr series id to its requested season numbers and request ids."""

    grouped: dict[int, dict[int, str]] = {}
    for record in await repository.list_sonarr_requests():
        if record.sonarr_series_id is None or record.season_number is None:
            continue
        grouped.setdefault(record.sonarr_series_id, {})[record.season_number] = record.id
    return grouped


async def requested_movies(
    repository: MediaRequestRepository,
) -> dict[int, MediaRequestRecord]:
    """Map each Radarr movie id to its request."""

    requested: dict[int, MediaRequestRecord] = {}
    for record in await repository.list_radarr_requests():
        if record.radarr_movie_id is None:
            continue
        requested[record.radarr_movie_id] = record
    return requested


__all__ = ["requested_movies", "requested_seasons_by_series"]
