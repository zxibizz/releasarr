"""Withdraw the monitoring behind a request, and the title nothing is left of.

Unmonitoring is what makes a removal stick - the recurring sync hands back a
request for every monitored season Sonarr still reports as missing - but it
leaves the library entry behind. For a title releasarr itself added a moment
ago, and for one whose last wanted season has just gone, that entry is the only
thing left of it. These helpers settle whether that is the case and, when it is,
delete the title from the app that holds it.
"""

from __future__ import annotations

from typing import Protocol

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.sonarr import SonarrService


class SupportsInfo(Protocol):
    """The one call these helpers make, leaving the caller's logger its own type.

    ``get_logger()`` and ``loguru._logger.Logger`` are different classes to mypy,
    and a use case holds the union of the two, so the piece actually used is
    named here and the call sites cast to it.
    """

    def info(self, message: str, **kwargs: object) -> None: ...


async def drop_series_if_unwanted(
    *,
    sonarr: SonarrService,
    repository: MediaRequestRepository,
    series_id: int,
    logger: SupportsInfo,
) -> bool:
    """Delete a Sonarr series nothing is left of, and report whether it went.

    Sonarr is asked rather than the answer inferred from what releasarr just
    unmonitored, because Sonarr is the one holding the monitoring: a season
    monitored outside releasarr keeps the series alive, and so does the
    future-seasons flag, which is a series wanting something with no season of
    its own monitored.

    A file on disk keeps the series as well. Releasarr did not put it there, and
    the delete asked for leaves files alone, so the entry they would be imported
    through is worth more than the tidiness of removing it. A request of ours
    still naming the series keeps it for the same kind of reason: the sync
    watches over that request, and it would be left pointing at a series Sonarr
    no longer holds.
    """

    if any(
        record.sonarr_series_id == series_id for record in await repository.list_sonarr_requests()
    ):
        return False
    details = await sonarr.get_series(series_id)
    if details.monitor_new_seasons:
        return False
    if any(season.monitored for season in details.seasons.values()):
        return False
    if any(season.episode_file_count for season in details.seasons.values()):
        return False

    await sonarr.delete_series(series_id)
    logger.info(
        "Deleted series with nothing left of it",
        sonarr_series_id=series_id,
        series_title=details.title,
    )
    return True


async def drop_movie_if_unwanted(
    *,
    radarr: RadarrService,
    repository: MediaRequestRepository,
    movie_id: int,
    logger: SupportsInfo,
) -> bool:
    """Delete a Radarr movie nothing is left of, and report whether it went.

    A movie has no seasons to be monitored, so a file is the whole of the
    question: with none, the library entry is all that is left of it.
    """

    if any(
        record.radarr_movie_id == movie_id for record in await repository.list_radarr_requests()
    ):
        return False

    movie = await radarr.get_movie(movie_id)
    if movie.has_file:
        return False

    await radarr.delete_movie(movie_id)
    logger.info(
        "Deleted movie with nothing left of it", radarr_movie_id=movie_id, movie_title=movie.title
    )
    return True


__all__ = ["SupportsInfo", "drop_movie_if_unwanted", "drop_series_if_unwanted"]
