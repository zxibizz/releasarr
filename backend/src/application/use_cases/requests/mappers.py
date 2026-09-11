"""Mapping helpers for media request entities."""

from __future__ import annotations

from src.application.interfaces.media_requests import MediaLocalization, MediaRequestRecord
from src.application.use_cases.requests.dto import (
    MediaRequestDTO,
    MediaRequestsPageDTO,
    MovieRequestDTO,
    SeriesRequestDTO,
)
from src.domain.enums import MediaType


def record_to_dto(record: MediaRequestRecord) -> MediaRequestDTO:
    """Convert a repository record into a DTO for API consumption."""

    genres = list(record.genres) if record.genres else []
    poster_url = record.poster_url or ""
    overview = record.overview or ""
    imdb_id = record.imdb_id or ""

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
            runtime=record.runtime_minutes or 0,
            imdb_id=imdb_id,
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
        season_number=record.season_number or 0,
        total_episodes=record.total_episodes or 0,
        series_title=record.series_title or record.title,
        series_year=record.series_year or record.year,
        imdb_id=imdb_id,
        sonarr_series_id=record.sonarr_series_id,
    )


def records_to_page(
    records: list[MediaRequestRecord],
    *,
    total: int,
    page: int,
    per_page: int,
) -> MediaRequestsPageDTO:
    """Convert paginated repository results into DTO form."""

    dtos = [record_to_dto(record) for record in records]
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
