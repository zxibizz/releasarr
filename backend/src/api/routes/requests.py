"""FastAPI routes for media request operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from src.api.dependencies import require_api_key
from src.api.errors import api_error
from src.api.responses import error_responses
from src.application.interfaces.media_requests import MediaLocalization as MediaLocalizationData
from src.application.use_cases.requests import (
    CreateMediaRequestUseCase,
    CreateMovieRequestCommand,
    CreateSeriesRequestCommand,
    DeleteMediaRequestUseCase,
    GetMediaRequestUseCase,
    ListMediaRequestsUseCase,
    ListRequestsOptions,
    MediaRequestDTO,
    MediaRequestsPageDTO,
    MovieRequestDTO,
    SeriesRequestDTO,
    UpdateMediaRequestCommand,
    UpdateMediaRequestUseCase,
)
from src.core.container import AppContainer, get_container
from src.domain.enums import MediaRequestStatus, MediaType
from src.schemas.requests import (
    CreateMovieRequest,
    CreateSeriesRequest,
    MediaRequest,
    MediaRequestCreate,
    MediaRequestUpdate,
    MovieRequest,
    RequestsResponse,
    SeriesRequest,
)
from src.schemas.requests import (
    MediaLocalization as MediaLocalizationSchema,
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


_SERVER_ERROR = "Unexpected server error."

LIST_REQUESTS_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Invalid pagination or filter parameters.",
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


def _page_to_response(page: MediaRequestsPageDTO) -> RequestsResponse:
    requests = [_dto_to_schema(dto) for dto in page.requests]
    return RequestsResponse(
        requests=requests, total=page.total, page=page.page, per_page=page.per_page
    )


@router.get("", response_model=RequestsResponse, responses=LIST_REQUESTS_RESPONSES)
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
    get_use_case: GetMediaRequestUseCase = Depends(_get_get_use_case),
) -> MediaRequest:
    dto = await get_use_case.execute(request_id)
    return _dto_to_schema(dto)


@router.patch(
    "/{requestId}",
    response_model=MediaRequest,
    responses=UPDATE_REQUEST_RESPONSES,
)
async def update_request(
    request_id: RequestIdParam,
    payload: MediaRequestUpdate,
    update_use_case: UpdateMediaRequestUseCase = Depends(_get_update_use_case),
) -> MediaRequest:
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
    delete_use_case: DeleteMediaRequestUseCase = Depends(_get_delete_use_case),
) -> Response:
    await delete_use_case.execute(request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
