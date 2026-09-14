"""FastAPI routes for media request operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from src.api.dependencies import require_user
from src.api.errors import api_error
from src.api.responses import error_responses
from src.api.routes.discover import seasons_to_schema
from src.application.interfaces.media_requests import MediaLocalization as MediaLocalizationData
from src.application.use_cases.auth import Principal
from src.application.use_cases.discover import (
    ListRequestSeasonsUseCase,
    UpdateRequestSeasonsCommand,
    UpdateRequestSeasonsUseCase,
)
from src.application.use_cases.requests import (
    CreateMediaRequestUseCase,
    CreateMovieRequestCommand,
    CreateSeriesRequestCommand,
    DeleteMediaRequestUseCase,
    GetMediaRequestUseCase,
    ListMediaRequestsUseCase,
    ListRequestEpisodesUseCase,
    ListRequestsOptions,
    MediaRequestDTO,
    MediaRequestNotFoundError,
    MediaRequestsPageDTO,
    MovieRequestDTO,
    SeasonEpisodesDTO,
    SeriesRequestDTO,
    UpdateMediaRequestCommand,
    UpdateMediaRequestUseCase,
)
from src.core.container import AppContainer, get_container
from src.domain.enums import MediaRequestStatus, MediaType
from src.schemas.discover import SeriesSeasonsResponse, UpdateSeasonsPayload
from src.schemas.requests import (
    CreateMovieRequest,
    CreateSeriesRequest,
    MediaRequest,
    MediaRequestCreate,
    MediaRequestUpdate,
    MovieRequest,
    RequestsResponse,
    SeasonEpisode,
    SeasonEpisodesResponse,
    SeriesRequest,
)
from src.schemas.requests import (
    MediaLocalization as MediaLocalizationSchema,
)

router = APIRouter(prefix="/requests", tags=["Requests"], dependencies=[Depends(require_user)])


def _get_container() -> AppContainer:
    return get_container()


def _get_list_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListMediaRequestsUseCase:
    return container.use_cases.media_requests.list


def _get_create_use_case(
    container: AppContainer = Depends(_get_container),
) -> CreateMediaRequestUseCase:
    return container.use_cases.media_requests.create


def _get_get_use_case(container: AppContainer = Depends(_get_container)) -> GetMediaRequestUseCase:
    return container.use_cases.media_requests.get


def _get_update_use_case(
    container: AppContainer = Depends(_get_container),
) -> UpdateMediaRequestUseCase:
    return container.use_cases.media_requests.update


def _get_delete_use_case(
    container: AppContainer = Depends(_get_container),
) -> DeleteMediaRequestUseCase:
    return container.use_cases.media_requests.delete


def _get_seasons_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListRequestSeasonsUseCase:
    return container.use_cases.discover.request_seasons


def _get_update_seasons_use_case(
    container: AppContainer = Depends(_get_container),
) -> UpdateRequestSeasonsUseCase:
    return container.use_cases.discover.update_request_seasons


def _get_episodes_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListRequestEpisodesUseCase:
    return container.use_cases.media_requests.episodes


_SERVER_ERROR = "Unexpected server error."
_UPSTREAM_ERROR = "Sonarr or Radarr could not be reached."
_UNMANAGEABLE_SEASONS = "The request has no series in Sonarr whose seasons can be managed."
_NO_EPISODES = "The request has no season in Sonarr whose episodes can be listed."

LIST_REQUESTS_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Invalid pagination or filter parameters.",
        status.HTTP_403_FORBIDDEN: "Restricted callers may not filter requests by owner.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

CREATE_REQUEST_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Malformed request payload.",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation failed for the provided fields.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

GET_REQUEST_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "Request not found.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

UPDATE_REQUEST_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Malformed request body.",
        status.HTTP_404_NOT_FOUND: "Request not found.",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation failed for at least one field.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

DELETE_REQUEST_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "Request not found.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

SEASONS_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "Request not found.",
        status.HTTP_409_CONFLICT: _UNMANAGEABLE_SEASONS,
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

UPDATE_SEASONS_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "The series has no such season.",
        status.HTTP_404_NOT_FOUND: "Request not found.",
        status.HTTP_409_CONFLICT: _UNMANAGEABLE_SEASONS,
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation failed for the provided fields.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)


EPISODES_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "Request not found.",
        status.HTTP_409_CONFLICT: _NO_EPISODES,
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)


RequestIdParam = Annotated[str, Path(..., alias="requestId")]


def _dto_to_schema(dto: MediaRequestDTO) -> MediaRequest:
    if isinstance(dto, MovieRequestDTO):
        return MovieRequest.model_validate(dto)
    if isinstance(dto, SeriesRequestDTO):
        return SeriesRequest.model_validate(dto)
    raise TypeError("Unsupported DTO type")


def _guard_scope(principal: Principal, request_id: str, owner_user_id: str | None) -> None:
    """Raise ``MediaRequestNotFoundError`` for a request outside the caller's scope.

    Not-found rather than forbidden: a 403 would confirm the request exists.
    """

    if not principal.scope.permits(owner_user_id):
        raise MediaRequestNotFoundError(request_id)


def _episodes_to_schema(dto: SeasonEpisodesDTO) -> SeasonEpisodesResponse:
    return SeasonEpisodesResponse(
        season_number=dto.season_number,
        episodes=[
            SeasonEpisode(
                episode_number=episode.episode_number,
                title=episode.title,
                status=episode.status,
                air_date=episode.air_date,
                file_size=episode.file_size,
            )
            for episode in dto.episodes
        ],
    )


def _page_to_response(page: MediaRequestsPageDTO) -> RequestsResponse:
    requests = [_dto_to_schema(dto) for dto in page.requests]
    return RequestsResponse(
        requests=requests, total=page.total, page=page.page, per_page=page.per_page
    )


@router.get("", response_model=RequestsResponse, responses=LIST_REQUESTS_RESPONSES)
async def list_requests(
    principal: Principal = Depends(require_user),
    list_use_case: ListMediaRequestsUseCase = Depends(_get_list_use_case),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
    owner: str | None = Query(default=None),
) -> RequestsResponse:
    status_value: MediaRequestStatus | None = None
    if status_filter:
        try:
            status_value = MediaRequestStatus(status_filter)
        except ValueError as exc:  # pragma: no cover - validated by FastAPI but kept defensive
            raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_status_filter", str(exc)) from exc

    media_type: MediaType | None = None
    if type_filter:
        try:
            media_type = MediaType(type_filter)
        except ValueError as exc:
            raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_type_filter", str(exc)) from exc

    scope = principal.scope
    if owner is not None and scope.is_restricted:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "forbidden", "You may not filter requests by owner"
        )
    owner_filter = scope.owner_user_id if scope.is_restricted else owner

    options = ListRequestsOptions(
        page=page,
        per_page=per_page,
        status=status_value,
        media_type=media_type,
        owner_user_id=owner_filter,
    )
    result = await list_use_case.execute(options)
    return _page_to_response(result)


@router.post(
    "",
    response_model=MediaRequest,
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_REQUEST_RESPONSES,
)
async def create_request(
    payload: MediaRequestCreate,
    create_use_case: CreateMediaRequestUseCase = Depends(_get_create_use_case),
) -> MediaRequest:
    command = _build_create_command(payload)
    dto = await create_use_case.execute(command)
    return _dto_to_schema(dto)


@router.get(
    "/{requestId}",
    response_model=MediaRequest,
    responses=GET_REQUEST_RESPONSES,
)
async def get_request(
    request_id: RequestIdParam,
    principal: Principal = Depends(require_user),
    get_use_case: GetMediaRequestUseCase = Depends(_get_get_use_case),
) -> MediaRequest:
    dto = await get_use_case.execute(request_id)
    _guard_scope(principal, request_id, dto.owner_user_id)
    return _dto_to_schema(dto)


@router.patch(
    "/{requestId}",
    response_model=MediaRequest,
    responses=UPDATE_REQUEST_RESPONSES,
)
async def update_request(
    request_id: RequestIdParam,
    payload: MediaRequestUpdate,
    principal: Principal = Depends(require_user),
    get_use_case: GetMediaRequestUseCase = Depends(_get_get_use_case),
    update_use_case: UpdateMediaRequestUseCase = Depends(_get_update_use_case),
) -> MediaRequest:
    if "owner_user_id" in payload.model_fields_set and not principal.is_admin:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "forbidden", "Only an admin may reassign a request's owner"
        )
    if principal.scope.is_restricted:
        existing = await get_use_case.execute(request_id)
        _guard_scope(principal, request_id, existing.owner_user_id)
    command = _build_update_command(payload)
    dto = await update_use_case.execute(request_id, command)
    return _dto_to_schema(dto)


@router.delete(
    "/{requestId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=DELETE_REQUEST_RESPONSES,
)
async def delete_request(
    request_id: RequestIdParam,
    principal: Principal = Depends(require_user),
    get_use_case: GetMediaRequestUseCase = Depends(_get_get_use_case),
    delete_use_case: DeleteMediaRequestUseCase = Depends(_get_delete_use_case),
) -> Response:
    if principal.scope.is_restricted:
        existing = await get_use_case.execute(request_id)
        _guard_scope(principal, request_id, existing.owner_user_id)
    await delete_use_case.execute(request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{requestId}/seasons",
    response_model=SeriesSeasonsResponse,
    responses=SEASONS_RESPONSES,
)
async def list_request_seasons(
    request_id: RequestIdParam,
    seasons_use_case: ListRequestSeasonsUseCase = Depends(_get_seasons_use_case),
) -> SeriesSeasonsResponse:
    seasons = await seasons_use_case.execute(request_id)
    return seasons_to_schema(seasons)


@router.get(
    "/{requestId}/episodes",
    response_model=SeasonEpisodesResponse,
    responses=EPISODES_RESPONSES,
)
async def list_request_episodes(
    request_id: RequestIdParam,
    episodes_use_case: ListRequestEpisodesUseCase = Depends(_get_episodes_use_case),
) -> SeasonEpisodesResponse:
    episodes = await episodes_use_case.execute(request_id)
    return _episodes_to_schema(episodes)


@router.put(
    "/{requestId}/seasons",
    response_model=SeriesSeasonsResponse,
    responses=UPDATE_SEASONS_RESPONSES,
)
async def update_request_seasons(
    request_id: RequestIdParam,
    payload: UpdateSeasonsPayload,
    update_seasons_use_case: UpdateRequestSeasonsUseCase = Depends(_get_update_seasons_use_case),
) -> SeriesSeasonsResponse:
    command = UpdateRequestSeasonsCommand(
        season_numbers=list(payload.season_numbers),
        monitor_new_seasons=payload.monitor_new_seasons,
    )
    seasons = await update_seasons_use_case.execute(request_id, command)
    return seasons_to_schema(seasons)


def _build_create_command(
    payload: MediaRequestCreate,
) -> CreateMovieRequestCommand | CreateSeriesRequestCommand:
    if isinstance(payload, CreateMovieRequest):
        localizations = _schema_to_localizations(payload.localizations)
        return CreateMovieRequestCommand(
            title=payload.title,
            year=payload.year,
            runtime=payload.runtime,
            imdb_id=payload.imdb_id,
            overview=payload.overview,
            poster_url=payload.poster_url,
            genres=payload.genres,
            localizations=localizations or None,
        )
    if isinstance(payload, CreateSeriesRequest):
        localizations = _schema_to_localizations(payload.localizations)
        return CreateSeriesRequestCommand(
            title=payload.title,
            year=payload.year,
            season_number=payload.season_number,
            total_episodes=payload.total_episodes,
            series_title=payload.series_title,
            series_year=payload.series_year,
            imdb_id=payload.imdb_id,
            overview=payload.overview,
            poster_url=payload.poster_url,
            genres=payload.genres,
            localizations=localizations or None,
        )
    msg = f"Unsupported media type '{payload.type}'"
    raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_media_type", msg)


def _build_update_command(payload: MediaRequestUpdate) -> UpdateMediaRequestCommand:
    command = UpdateMediaRequestCommand()
    for field_name in payload.model_fields_set:
        value = getattr(payload, field_name)
        if field_name == "status" and value is not None:
            value = MediaRequestStatus(value)
        if field_name == "localizations":
            value = _schema_to_localizations(value)
        setattr(command, field_name, value)
    return command


def _schema_to_localizations(
    localizations: dict[str, MediaLocalizationSchema] | None,
) -> dict[str, MediaLocalizationData]:
    if not localizations:
        return {}
    return {
        language.lower(): MediaLocalizationData(
            title=value.title,
            overview=value.overview,
        )
        for language, value in localizations.items()
    }


__all__ = ["router"]
