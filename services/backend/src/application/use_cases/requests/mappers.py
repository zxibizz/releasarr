"""Mapping helpers for media request entities."""

from __future__ import annotations

from collections.abc import Sequence

from src.application.interfaces.media_requests import MediaLocalization, MediaRequestRecord
from src.application.interfaces.request_warnings import RequestWarningRecord
from src.application.use_cases.requests.dto import (
    MediaRequestDTO,
    MediaRequestsPageDTO,
    MovieRequestDTO,
    RequestWarningDTO,
    SeriesEpisodeCountsDTO,
    SeriesRequestDTO,
)
from src.domain.enums import MediaType


def _warning_to_dto(warning: RequestWarningRecord) -> RequestWarningDTO:
    # Always populated by the repository on read; only optional on the write side.
    assert warning.created_at is not None, "a read-back warning row always has created_at"
    return RequestWarningDTO(
        code=warning.code,
        release_id=warning.release_id,
        details=warning.details,
        created_at=warning.created_at,
    )


def record_to_dto(
    record: MediaRequestRecord,
    warnings: Sequence[RequestWarningRecord] = (),
) -> MediaRequestDTO:
    """Convert a repository record into a DTO for API consumption."""

    genres = list(record.genres) if record.genres else []
    poster_url = record.poster_url or ""
    overview = record.overview or ""
    imdb_id = record.imdb_id or ""
    warning_dtos = [_warning_to_dto(warning) for warning in warnings]

    if record.media_type == MediaType.MOVIE:
        return MovieRequestDTO(
            id=record.id,
            title=record.title,
            year=record.year,
            poster_url=poster_url,
            overview=overview,
            genres=genres,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
            localizations=_clone_localizations(record.localizations),
            exported_at=record.exported_at,
            newest_release_published_at=record.newest_release_published_at,
            runtime=record.runtime_minutes or 0,
            imdb_id=imdb_id,
            radarr_movie_id=record.radarr_movie_id,
            owner_user_id=record.owner_user_id,
            warnings=warning_dtos,
        )

    # Derive episode counts when Sonarr-provided aired/downloaded values exist.
    if record.aired_episodes is None:
        episode_counts = None
    else:
        downloaded = max(record.downloaded_episodes or 0, 0)
        aired = max(record.aired_episodes or 0, 0)
        total = record.total_episodes or 0
        pending = max(aired - downloaded, 0)
        unaired = max(total - aired, 0)
        episode_counts = SeriesEpisodeCountsDTO(
            downloaded=downloaded,
            pending=pending,
            unaired=unaired,
        )

    return SeriesRequestDTO(
        id=record.id,
        title=record.title,
        year=record.year,
        poster_url=poster_url,
        overview=overview,
        genres=genres,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        localizations=_clone_localizations(record.localizations),
        exported_at=record.exported_at,
        newest_release_published_at=record.newest_release_published_at,
        season_number=record.season_number or 0,
        total_episodes=record.total_episodes or 0,
        series_title=record.series_title or record.title,
        series_year=record.series_year or record.year,
        imdb_id=imdb_id,
        sonarr_series_id=record.sonarr_series_id,
        episode_counts=episode_counts,
        owner_user_id=record.owner_user_id,
        warnings=warning_dtos,
    )


def records_to_page(
    records: list[MediaRequestRecord],
    *,
    total: int,
    page: int,
    per_page: int,
    warnings_by_request: dict[str, list[RequestWarningRecord]] | None = None,
) -> MediaRequestsPageDTO:
    """Convert paginated repository results into DTO form."""

    warnings_by_request = warnings_by_request or {}
    dtos = [record_to_dto(record, warnings_by_request.get(record.id, ())) for record in records]
    return MediaRequestsPageDTO(requests=dtos, total=total, page=page, per_page=per_page)


def _clone_localizations(
    localizations: dict[str, MediaLocalization],
) -> dict[str, MediaLocalization]:
    if not localizations:
        return {}
    return {
        language: MediaLocalization(
            title=value.title,
            overview=value.overview,
        )
        for language, value in localizations.items()
    }


__all__ = ["record_to_dto", "records_to_page"]
