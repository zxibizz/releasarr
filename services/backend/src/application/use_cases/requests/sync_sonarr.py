"""Synchronise media requests with the seasons Sonarr monitors."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast
from uuid import uuid4

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.sonarr import SeriesDetails, SonarrService
from src.application.interfaces.tvdb import TvdbSeriesMetadata, TvdbService
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import ArrCompletion, season_completion
from src.application.utility.localization import (
    LocalizationPicker,
    merge_default_localization,
)
from src.application.utility.metadata_cache import SupportsWarning, get_cached_metadata
from src.application.utility.sentinels import UNSET, _Unset
from src.core.logging import get_logger
from src.domain.enums import LogComponent, MediaRequestStatus, MediaType


@dataclass(slots=True)
class SyncSonarrResult:
    """Summary of the performed synchronisation."""

    created: int = 0
    updated: int = 0
    deleted: int = 0


class SyncSonarrMediaRequestsUseCase:
    """Reconcile media requests with the seasons Sonarr monitors."""

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        tvdb_service: TvdbService,
        recompute_state: RecomputeRequestStateUseCase,
        metadata_languages: Sequence[str] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._tvdb = tvdb_service
        self._recompute_state = recompute_state
        self._localization = LocalizationPicker(metadata_languages)
        self._metadata_languages = self._localization.languages
        self._logger = logger or get_logger(LogComponent.USECASE_SYNC_SONARR)
        self._metadata_cache: dict[int, TvdbSeriesMetadata | None] = {}

    async def execute(self) -> SyncSonarrResult:
        """Reconcile media requests with the seasons Sonarr monitors."""

        result = SyncSonarrResult()
        self._metadata_cache.clear()
        library = await self._sonarr.list_series()

        # The monitored seasons of every series are what releasarr tracks. A
        # series whose add options are still set is mid-scan and its season flags
        # are about to be rewritten, so it is left out of both adoption and
        # pruning until next time.
        wanted: dict[tuple[int, int], SeriesDetails] = {}
        unsettled: set[int] = set()
        for details in library:
            if details.has_add_options:
                unsettled.add(details.id)
                continue
            for season in details.seasons.values():
                if season.monitored:
                    wanted[(details.id, season.season_number)] = details

        existing = await self._repository.list_sonarr_requests()
        existing_keys = {
            (record.sonarr_series_id, record.season_number): record
            for record in existing
            if record.sonarr_series_id is not None and record.season_number is not None
        }

        # Sonarr is the authority: a request whose season it no longer monitors -
        # or whose series is gone - has nothing left to be, so the row goes with
        # it. An empty library skips the pass so a Sonarr answering 200 with
        # nothing during a restart does not wipe every request.
        if not library and existing:
            self._logger.warning(
                "Sonarr reported an empty library; skipping request pruning",
                existing_requests=len(existing),
            )
        else:
            for key, record in existing_keys.items():
                if key in wanted or key[0] in unsettled:
                    continue
                await self._repository.delete_request(record.id)
                result.deleted += 1
                self._logger.info(
                    "Deleted request for a season Sonarr no longer monitors",
                    request_id=record.id,
                    sonarr_series_id=record.sonarr_series_id,
                    season_number=record.season_number,
                    request_title=record.title,
                )

        # Every surviving request gets exactly one verdict, derived from Sonarr's
        # own season counts; the recompute is the only writer of status.
        verdicts: dict[str, ArrCompletion] = {}

        # A series' seasons are normally all requested by the same person, so a
        # newly monitored season under "monitor future seasons" should default to
        # whoever already owns the series rather than come back unowned.
        series_owners: dict[int, str] = {}
        for record in sorted(existing, key=lambda r: r.created_at, reverse=True):
            if (
                record.sonarr_series_id is not None
                and record.owner_user_id is not None
                and record.sonarr_series_id not in series_owners
            ):
                series_owners[record.sonarr_series_id] = record.owner_user_id

        for (series_id, season_number), details in wanted.items():
            outcome = await self._sync_season(
                details,
                season_number,
                owner_user_id=series_owners.get(series_id),
                verdicts=verdicts,
            )
            if outcome == "created":
                result.created += 1
            elif outcome == "updated":
                result.updated += 1

        if verdicts:
            await self._recompute_state.execute(sorted(verdicts), arr_completion=verdicts)

        self._logger.info(
            "Sonarr sync finished",
            created=result.created,
            updated=result.updated,
            deleted=result.deleted,
        )
        return result

    async def sync_series(
        self,
        series_id: int,
        season_numbers: Sequence[int],
        *,
        owner_user_id: str | None = None,
    ) -> list[str]:
        """Create or refresh requests for named seasons of a single series.

        Serves the add-request flow, where the seasons to cover are known and the
        request has to exist by the time the call returns. Completing and pruning
        belong to the full sweep alone.
        """

        self._metadata_cache.clear()
        details = await self._sonarr.get_series(series_id)

        request_ids: list[str] = []
        for season_number in sorted(set(season_numbers)):
            await self._sync_season(
                details, season_number, owner_user_id=owner_user_id, reopen_completed=True
            )
            record = await self._repository.find_by_sonarr(
                sonarr_series_id=series_id,
                season_number=season_number,
            )
            if record is not None:
                request_ids.append(record.id)
        return request_ids

    async def _sync_season(
        self,
        details: SeriesDetails,
        season_number: int,
        *,
        owner_user_id: str | None = None,
        verdicts: dict[str, ArrCompletion] | None = None,
        reopen_completed: bool = False,
    ) -> str:
        """Create or update a Sonarr-backed request for a specific season."""

        existing = await self._repository.find_by_sonarr(
            sonarr_series_id=details.id,
            season_number=season_number,
        )

        season_info = details.seasons.get(season_number)
        # A season the library read has no entry for - an empty season Sonarr
        # only reports a row for, say - counts as incomplete until it has numbers.
        verdict = (
            season_completion(season_info)
            if season_info is not None
            else ArrCompletion(is_complete=False)
        )

        # TVDB is the expensive leg of the sweep, and only the translations a row
        # is missing justify it; everything else comes from Sonarr itself.
        metadata: TvdbSeriesMetadata | None = None
        if existing is not None and existing.localizations:
            localizations = existing.localizations
        else:
            metadata = await self._load_tvdb_metadata(details)
            localizations = self._build_localizations(metadata, details, season_number)

        total_episodes = season_info.total_episode_count if season_info else 0
        aired_episodes = season_info.episode_count if season_info else None
        downloaded_episodes = season_info.episode_file_count if season_info else None
        localized_series_title = self._localization.select(localizations, "title", details.title)
        title = self._build_request_title(localized_series_title, season_number)
        year = details.year or 0
        series_year = details.year or year
        genres = list(details.genres)
        imdb_id = details.imdb_id
        overview_value = self._localization.select(localizations, "overview", details.overview)
        overview = overview_value or None
        poster_url = details.poster_url or (metadata.image_url if metadata else None)

        if existing is None:
            data = CreateMediaRequestData(
                id=uuid4().hex,
                media_type=MediaType.SERIES,
                title=title,
                year=year,
                overview=overview,
                poster_url=poster_url,
                genres=genres,
                runtime_minutes=None,
                imdb_id=imdb_id,
                season_number=season_number,
                total_episodes=total_episodes,
                aired_episodes=aired_episodes,
                downloaded_episodes=downloaded_episodes,
                series_title=details.title,
                series_year=series_year,
                status=MediaRequestStatus.PENDING,
                sonarr_series_id=details.id,
                localizations=localizations,
                owner_user_id=owner_user_id,
            )
            await self._repository.create_request(data)
            self._logger.debug(
                "Created media request for Sonarr season",
                sonarr_series_id=details.id,
                season_number=season_number,
                request_title=title,
            )
            if verdicts is not None:
                verdicts[data.id] = verdict
            return "created"

        # What the verdict implies for the status is the recompute's call, not
        # this refresh's.
        if verdicts is not None:
            verdicts[existing.id] = verdict

        # Re-requesting a completed season by hand is user intent, which the
        # recompute has no signal for, so it is written directly. The next full
        # sync's verdict settles it again if nothing was grabbed meanwhile.
        status: MediaRequestStatus | _Unset = UNSET
        if reopen_completed and existing.status is MediaRequestStatus.COMPLETED:
            status = MediaRequestStatus.PENDING

        update = UpdateMediaRequestData(
            title=title,
            year=year,
            overview=overview,
            poster_url=poster_url,
            genres=genres,
            status=status,
            imdb_id=imdb_id,
            season_number=season_number,
            total_episodes=total_episodes,
            aired_episodes=aired_episodes,
            downloaded_episodes=downloaded_episodes,
            series_title=details.title,
            series_year=series_year,
            sonarr_series_id=details.id,
            localizations=localizations,
        )
        await self._repository.update_request(existing.id, update)
        self._logger.debug(
            "Updated media request for Sonarr season",
            request_id=existing.id,
            sonarr_series_id=details.id,
            season_number=season_number,
        )
        return "updated"

    def _build_request_title(self, series_title: str, season_number: int) -> str:
        if season_number <= 0:
            return f"{series_title} - Specials"
        return f"{series_title} - Season {season_number}"

    async def _load_tvdb_metadata(self, details: SeriesDetails) -> TvdbSeriesMetadata | None:
        if not self._tvdb.is_configured or details.tvdb_id is None:
            return None
        tvdb = self._tvdb
        tvdb_id = details.tvdb_id
        return await get_cached_metadata(
            cache=self._metadata_cache,
            lookup_id=tvdb_id,
            fetch=lambda: tvdb.get_series(tvdb_id, self._metadata_languages),
            logger=cast(SupportsWarning, self._logger),
            provider_name="sonarr_series_id",
            entity_id=details.id,
            lookup_field="tvdb_id",
            warning_message="Failed to fetch TVDB metadata",
        )

    def _build_localizations(
        self,
        metadata: TvdbSeriesMetadata | None,
        details: SeriesDetails,
        season_number: int,
    ) -> dict[str, MediaLocalization]:
        localizations: dict[str, MediaLocalization] = {}
        if metadata is not None:
            for language, translation in metadata.translations.items():
                season_overview = translation.season_overviews.get(season_number)
                localizations[language] = MediaLocalization(
                    title=translation.title,
                    overview=season_overview or translation.overview,
                )
        merge_default_localization(
            localizations,
            title=details.title,
            overview=details.overview,
        )
        return localizations


__all__ = ["SyncSonarrMediaRequestsUseCase", "SyncSonarrResult"]
