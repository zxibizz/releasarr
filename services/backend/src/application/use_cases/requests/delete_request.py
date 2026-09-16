"""Delete media requests, and withdraw the monitoring behind them."""

from __future__ import annotations

from typing import cast

from loguru._logger import Logger

from src.application.interfaces.media_requests import MediaRequestRecord, MediaRequestRepository
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.application.use_cases.requests.withdrawal import (
    SupportsInfo,
    drop_movie_if_unwanted,
    drop_series_if_unwanted,
)
from src.core.logging import get_logger


class DeleteMediaRequestUseCase:
    """Use case responsible for removing media requests.

    Dropping the row on its own does not remove much for long: the recurring
    sync builds a request for every monitored season Sonarr still reports as
    missing, so the next run would hand straight back what was just removed.
    Unmonitoring in Sonarr or Radarr is what makes the removal stick.

    A file already imported is left where it is, and the title it belongs to is
    left with it. A title releasarr asked for and nothing is left of, though -
    no season monitored, no file on disk - is deleted outright: the library
    entry is all that is left of it, and the next add would only rebuild it.
    """

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._radarr = radarr_service
        self._logger = logger or get_logger(component="delete_media_request")

    async def execute(self, request_id: str) -> None:
        record = await self._repository.get_request(request_id)
        if record is None:
            raise MediaRequestNotFoundError(request_id)

        # Unmonitored first: a row deleted while its season is still wanted
        # reappears, whereas a season unmonitored while the row survives is
        # merely stale, and the next sync tidies it up.
        await self.unmonitor(record)

        deleted = await self._repository.delete_request(request_id)
        if not deleted:
            raise MediaRequestNotFoundError(request_id)

        # After the row, so that a request of ours still naming this series is
        # one of somebody else's and keeps the title in the library.
        await self._drop_what_is_left_of(record)

    async def _drop_what_is_left_of(self, record: MediaRequestRecord) -> None:
        """Delete the series or movie this request was the last of."""

        if record.sonarr_series_id is not None:
            await drop_series_if_unwanted(
                sonarr=self._sonarr,
                repository=self._repository,
                series_id=record.sonarr_series_id,
                logger=cast(SupportsInfo, self._logger),
            )
        elif record.radarr_movie_id is not None:
            await drop_movie_if_unwanted(
                radarr=self._radarr,
                repository=self._repository,
                movie_id=record.radarr_movie_id,
                logger=cast(SupportsInfo, self._logger),
            )

    async def unmonitor(self, record: MediaRequestRecord) -> None:
        """Tell Sonarr or Radarr that this request is no longer wanted.

        A request that never reached either app - the ones created straight
        through the API carry no library id - has no monitoring to withdraw.

        Only the season is named, and the series follows from it: withdrawing
        the last season it had monitored leaves the series unmonitored too,
        rather than one that wants none of itself.
        """

        if record.sonarr_series_id is not None and record.season_number is not None:
            await self._sonarr.apply_season_monitoring(
                record.sonarr_series_id,
                unmonitor=[record.season_number],
            )
            self._logger.info(
                "Unmonitored season for removed request",
                request_id=record.id,
                sonarr_series_id=record.sonarr_series_id,
                season=record.season_number,
            )
        elif record.radarr_movie_id is not None:
            await self._radarr.set_movie_monitored(record.radarr_movie_id, monitored=False)
            self._logger.info(
                "Unmonitored movie for removed request",
                request_id=record.id,
                radarr_movie_id=record.radarr_movie_id,
            )


__all__ = ["DeleteMediaRequestUseCase"]
