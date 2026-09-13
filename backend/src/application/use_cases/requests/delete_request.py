"""Delete media requests, and withdraw the monitoring behind them."""

from __future__ import annotations

from loguru._logger import Logger

from src.application.interfaces.media_requests import MediaRequestRecord, MediaRequestRepository
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.sonarr import SonarrService
from src.application.use_cases.requests.exceptions import MediaRequestNotFoundError
from src.core.logging import get_logger


class DeleteMediaRequestUseCase:
    """Use case responsible for removing media requests.

    Dropping the row on its own does not remove much for long: the recurring
    sync builds a request for every monitored season Sonarr still reports as
    missing, so the next run would hand straight back what was just removed.
    Unmonitoring in Sonarr or Radarr is what makes the removal stick.

    The series or movie itself stays in the library, as do any files already
    imported. Only what releasarr asked for is withdrawn.
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

    async def unmonitor(self, record: MediaRequestRecord) -> None:
        """Tell Sonarr or Radarr that this request is no longer wanted.

        A request that never reached either app - the ones created straight
        through the API carry no library id - has no monitoring to withdraw.
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
