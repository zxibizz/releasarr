"""FastAPI routes for media request operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from src.api.dependencies import require_api_key
from src.api.errors import api_error
from src.application.use_cases.requests import (
    CreateMediaRequestUseCase,
    CreateMovieRequestCommand,
    CreateSeriesRequestCommand,
    DeleteMediaRequestUseCase,
    EmptyUpdatePayloadError,
    GetMediaRequestUseCase,
    ListMediaRequestsUseCase,
    ListRequestsOptions,
    MediaRequestDTO,
    MediaRequestNotFoundError,
    MediaRequestsPageDTO,
    MovieRequestDTO,
    SeriesRequestDTO,
    UpdateMediaRequestCommand,
    UpdateMediaRequestUseCase,
)
from src.core.container import AppContainer, get_container
from src.domain.enums import MediaRequestStatus, MediaType
from src.schemas.requests import (
    MediaRequest,
    MediaRequestCreate,
    MediaRequestUpdate,
    MovieRequest,
    RequestsResponse,
    SeriesRequest,
)

router = APIRouter(prefix="/requests", tags=["Requests"], dependencies=[Depends(require_api_key)])


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


def _dto_to_schema(dto: MediaRequestDTO) -> MediaRequest:
    if isinstance(dto, MovieRequestDTO):
        return MovieRequest(
            id=dto.id,
            title=dto.title,
            year=dto.year,
            poster_url=dto.poster_url,
            overview=dto.overview,
            genres=list(dto.genres),
            status=dto.status.value,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            type=dto.type.value,
            runtime=dto.runtime,
            imdb_id=dto.imdb_id,
        )
    if isinstance(dto, SeriesRequestDTO):
        return SeriesRequest(
            id=dto.id,
            title=dto.title,
            year=dto.year,
            poster_url=dto.poster_url,
            overview=dto.overview,
            genres=list(dto.genres),
            status=dto.status.value,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            type=dto.type.value,
            season_number=dto.season_number,
            total_episodes=dto.total_episodes,
            series_title=dto.series_title,
            series_year=dto.series_year,
            imdb_id=dto.imdb_id,
        )
    raise TypeError("Unsupported DTO type")


def _page_to_response(page: MediaRequestsPageDTO) -> RequestsResponse:
    requests = [_dto_to_schema(dto) for dto in page.requests]
    return RequestsResponse(
        requests=requests, total=page.total, page=page.page, per_page=page.per_page
    )


@router.get("", response_model=RequestsResponse)
async def list_requests(
    list_use_case: ListMediaRequestsUseCase = Depends(_get_list_use_case),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    type_filter: str | None = Query(default=None, alias="type"),
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

    options = ListRequestsOptions(
        page=page,
        per_page=per_page,
        status=status_value,
        media_type=media_type,
    )
    result = await list_use_case.execute(options)
    return _page_to_response(result)


@router.post("", response_model=MediaRequest, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: MediaRequestCreate,
    create_use_case: CreateMediaRequestUseCase = Depends(_get_create_use_case),
) -> MediaRequest:
    command = _build_create_command(payload)
    dto = await create_use_case.execute(command)
    return _dto_to_schema(dto)


@router.get("/{request_id}", response_model=MediaRequest)
async def get_request(
    request_id: str,
    get_use_case: GetMediaRequestUseCase = Depends(_get_get_use_case),
) -> MediaRequest:
    try:
        dto = await get_use_case.execute(request_id)
    except MediaRequestNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "request_not_found", str(exc)) from exc
    return _dto_to_schema(dto)


@router.patch("/{request_id}", response_model=MediaRequest)
async def update_request(
    request_id: str,
    payload: MediaRequestUpdate,
    update_use_case: UpdateMediaRequestUseCase = Depends(_get_update_use_case),
) -> MediaRequest:
    command = _build_update_command(payload)
    try:
        dto = await update_use_case.execute(request_id, command)
    except EmptyUpdatePayloadError as exc:
        raise api_error(status.HTTP_400_BAD_REQUEST, "empty_update", str(exc)) from exc
    except MediaRequestNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "request_not_found", str(exc)) from exc
    return _dto_to_schema(dto)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(
    request_id: str,
    delete_use_case: DeleteMediaRequestUseCase = Depends(_get_delete_use_case),
) -> Response:
    deleted = await delete_use_case.execute(request_id)
    if not deleted:
        raise api_error(status.HTTP_404_NOT_FOUND, "request_not_found", "Media request not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _build_create_command(
    payload: MediaRequestCreate,
) -> CreateMovieRequestCommand | CreateSeriesRequestCommand:
    if payload.type == MediaType.MOVIE.value:
        return CreateMovieRequestCommand(
            title=payload.title,
            year=payload.year,
            runtime=payload.runtime,
            imdb_id=payload.imdb_id,
            overview=payload.overview,
            poster_url=payload.poster_url,
            genres=payload.genres,
        )
    if payload.type == MediaType.SERIES.value:
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
        )
    msg = f"Unsupported media type '{payload.type}'"
    raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_media_type", msg)


def _build_update_command(payload: MediaRequestUpdate) -> UpdateMediaRequestCommand:
    command = UpdateMediaRequestCommand()
    for field_name in payload.model_fields_set:
        value = getattr(payload, field_name)
        if field_name == "status" and value is not None:
            value = MediaRequestStatus(value)
        setattr(command, field_name, value)
    return command


__all__ = ["router"]
