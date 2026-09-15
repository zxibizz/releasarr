"""Synchronise media requests with missing Sonarr seasons."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from typing import cast
from uuid import uuid4

from loguru._logger import Logger

from src.application.interfaces.media_requests import (
    CreateMediaRequestData,
    MediaLocalization,
    MediaRequestRecord,
    MediaRequestRepository,
    UpdateMediaRequestData,
)
from src.application.interfaces.sonarr import SeriesDetails, SeriesSeasonDetails, SonarrService
from src.application.interfaces.tvdb import TvdbSeriesMetadata, TvdbService
from src.application.utility.localization import (
    LocalizationPicker,
    merge_default_localization,
)
from src.application.utility.metadata_cache import SupportsWarning, get_cached_metadata
from src.application.utility.sentinels import UNSET, _Unset
from src.core.logging import get_logger
from src.domain.enums import MediaRequestStatus, MediaType


@dataclass(slots=True)
class SyncSonarrResult:
    """Summary of the performed synchronisation."""

    created: int = 0
    updated: int = 0
    completed: int = 0


class SyncSonarrMediaRequestsUseCase:
    """Create or update media requests based on Sonarr missing seasons."""

    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        tvdb_service: TvdbService | None,
        metadata_languages: Sequence[str] | None = None,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._tvdb = tvdb_service
        self._localization = LocalizationPicker(metadata_languages)
        self._metadata_languages = self._localization.languages
        self._logger = logger or get_logger(component="sync_sonarr_requests")
        self._metadata_cache: dict[int, TvdbSeriesMetadata | None] = {}
        self._series_cache: dict[int, SeriesDetails] = {}

    async def execute(self) -> SyncSonarrResult:
        """Populate media requests for missing Sonarr seasons."""

        result = SyncSonarrResult()
        self._metadata_cache.clear()
        self._series_cache.clear()
        missing_series = await self._sonarr.get_missing_series()
        missing_keys = {
            (item.series_id, season_number)
            for item in missing_series
            for season_number in item.season_numbers
        }

        existing = await self._repository.list_sonarr_requests()
        result.completed += await self._mark_completed(existing, missing_keys)

        # A series' seasons are normally all requested by the same person, so a
        # newly missing season under "monitor future seasons" should default to
        # whoever already owns the series rather than come back unowned.
        series_owners: dict[int, str] = {}
        for record in sorted(existing, key=lambda r: r.created_at, reverse=True):
            if (
                record.sonarr_series_id is not None
                and record.owner_user_id is not None
                and record.sonarr_series_id not in series_owners
            ):
                series_owners[record.sonarr_series_id] = record.owner_user_id

        for series in missing_series:
            details = await self._series(series.series_id)
            owner_user_id = series_owners.get(series.series_id)
            for season_number in series.season_numbers:
                updated = await self._sync_season(
                    details, season_number, owner_user_id=owner_user_id
                )
                if updated == "created":
                    result.created += 1
                elif updated == "updated":
                    result.updated += 1

        self._logger.info(
            "Sonarr sync finished",
            created=result.created,
            updated=result.updated,
            completed=result.completed,
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
        request has to exist by the time the call returns. Sonarr's missing list
        is deliberately not consulted: a season whose episodes have not aired yet
        is absent from it, and the full sweep is what owns completing requests.
        """

        self._metadata_cache.clear()
        self._series_cache.clear()
        details = await self._series(series_id)

        request_ids: list[str] = []
        for season_number in sorted(set(season_numbers)):
            await self._sync_season(details, season_number, owner_user_id=owner_user_id)
            record = await self._repository.find_by_sonarr(
                sonarr_series_id=series_id,
                season_number=season_number,
            )
            if record is not None:
                request_ids.append(record.id)
        return request_ids

    async def _sync_season(
        self, details: SeriesDetails, season_number: int, *, owner_user_id: str | None = None
    ) -> str:
        """Create or update a Sonarr-backed request for a specific season."""

        existing = await self._repository.find_by_sonarr(
            sonarr_series_id=details.id,
            season_number=season_number,
        )

        metadata = await self._load_tvdb_metadata(details)
        localizations = self._build_localizations(metadata, details, season_number)

        season_info = details.seasons.get(season_number)
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
            return "created"

        # This is a metadata refresh for a season Sonarr still reports as missing.
        # Only a previously completed request needs to fall back to pending; an
        # in-flight status is owned by the release sync and must survive the refresh.
        status: MediaRequestStatus | _Unset = UNSET
        if existing.status == MediaRequestStatus.COMPLETED:
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

    async def _mark_completed(
        self,
        existing: list[MediaRequestRecord],
        missing_keys: set[tuple[int, int]],
    ) -> int:
        """Settle the Sonarr-linked requests Sonarr no longer reports as missing.

        Leaving the missing list is not the same as being finished. Sonarr drops a
        season from it as soon as every episode that has aired holds a file, so a
        season that is still airing leaves it weekly and returns the moment the
        next episode is wanted. Completing the request there would only have the
        next sync reopen it, so a season with episodes still to air is left on
        pending. That is also what keeps a release grabbed by hand actionable --
        nothing can re-grab it for the episodes that follow.
        """

        transitioned = 0
        for record in existing:
            if record.sonarr_series_id is None or record.season_number is None:
                continue
            key = (record.sonarr_series_id, record.season_number)
            if key in missing_keys:
                continue

            season = await self._settling_season(record)
            update = self._settled_update(record, season)
            if update is None:
                continue
            await self._repository.update_request(record.id, update)

            # A status transition belongs in the request's activity view, unlike
            # the metadata refresh above that runs on every sync.
            if update.status is MediaRequestStatus.COMPLETED:
                transitioned += 1
                self._logger.info(
                    "Marked Sonarr season as completed",
                    request_id=record.id,
                    sonarr_series_id=record.sonarr_series_id,
                    season_number=record.season_number,
                )
            elif update.status is MediaRequestStatus.PENDING:
                self._logger.info(
                    "Reopened Sonarr season with episodes still to air",
                    request_id=record.id,
                    sonarr_series_id=record.sonarr_series_id,
                    season_number=record.season_number,
                )
        return transitioned

    async def _series(self, series_id: int) -> SeriesDetails:
        """Return a series' details, asking Sonarr once per run.

        Both the completion sweep and the missing-season refresh want the same
        series, and a series is reported by several seasons.
        """

        details = self._series_cache.get(series_id)
        if details is None:
            details = await self._sonarr.get_series(series_id)
            self._series_cache[series_id] = details
        return details

    async def _settling_season(self, record: MediaRequestRecord) -> SeriesSeasonDetails | None:
        """Sonarr's live numbers for a season, when the stored ones leave a doubt.

        The counts on a request date from the last time the season was reported
        missing, because only that path rewrites them. A season that has left the
        missing list since then keeps them, and the card derives what is pending
        from them, so an episode Sonarr already holds goes on reading as one still
        to fetch. Those are the seasons worth a round trip: one whose stored
        counts have nothing outstanding is settled either way.
        """

        series_id = record.sonarr_series_id
        season_number = record.season_number
        if series_id is None or season_number is None:
            return None
        total_episodes = record.total_episodes
        aired_episodes = record.aired_episodes
        downloaded_episodes = record.downloaded_episodes
        if total_episodes is None or aired_episodes is None or downloaded_episodes is None:
            # A request that predates the counts has nothing to disagree with,
            # and asking anyway risks a series Sonarr has since dropped.
            return None
        if aired_episodes >= total_episodes and downloaded_episodes >= aired_episodes:
            return None
        return (await self._series(series_id)).seasons.get(season_number)

    @staticmethod
    def _settled_update(
        record: MediaRequestRecord,
        season: SeriesSeasonDetails | None,
    ) -> UpdateMediaRequestData | None:
        """What Sonarr's answer implies for a request it no longer calls missing.

        The stored counts are only trustworthy while a season is still reported
        missing, so a settled one is written from Sonarr's own numbers -- the same
        ones the missing-season refresh stores. Without an answer the stored
        counts stand, and a season Sonarr wants nothing more from has nothing left
        pending, which is what the completion has always recorded.

        Returns None when the request already says as much, so a season that needs
        neither a transition nor a correction is not rewritten on every sync.
        """

        unaired = season is not None and season.episode_count < season.total_episode_count
        status: MediaRequestStatus | _Unset
        if unaired:
            # Only a completed request is reopened: an in-flight status belongs
            # to the release sync and has to survive the sweep.
            status = (
                MediaRequestStatus.PENDING
                if record.status is MediaRequestStatus.COMPLETED
                else UNSET
            )
        elif record.status is MediaRequestStatus.COMPLETED:
            status = UNSET
        else:
            status = MediaRequestStatus.COMPLETED

        if season is None:
            update = UpdateMediaRequestData(
                status=status,
                downloaded_episodes=record.aired_episodes,
            )
        else:
            update = UpdateMediaRequestData(
                status=status,
                total_episodes=season.total_episode_count,
                aired_episodes=season.episode_count,
                downloaded_episodes=season.episode_file_count,
            )
        return update if _changes_record(record, update) else None

    def _build_request_title(self, series_title: str, season_number: int) -> str:
        if season_number <= 0:
            return f"{series_title} - Specials"
        return f"{series_title} - Season {season_number}"

    async def _load_tvdb_metadata(self, details: SeriesDetails) -> TvdbSeriesMetadata | None:
        if self._tvdb is None or details.tvdb_id is None:
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


def _changes_record(record: MediaRequestRecord, update: UpdateMediaRequestData) -> bool:
    """Whether applying `update` would change the record at all."""

    for field in fields(update):
        value = getattr(update, field.name)
        if value is not UNSET and getattr(record, field.name) != value:
            return True
    return False


__all__ = ["SyncSonarrMediaRequestsUseCase", "SyncSonarrResult"]
