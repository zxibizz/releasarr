"""FastAPI routes for finding media to request and adding it to Sonarr/Radarr."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from src.api.dependencies import require_api_key
from src.api.responses import error_responses
from src.application.use_cases.discover import (
    AddMediaRequestCommand,
    AddMediaRequestUseCase,
    ListRootFoldersUseCase,
    ListSeasonOptionsUseCase,
    MediaSearchResultDTO,
    SearchMediaUseCase,
    SeriesSeasonsDTO,
)
from src.application.use_cases.requests import (
    MediaRequestDTO,
    MovieRequestDTO,
    SeriesRequestDTO,
)
from src.core.container import AppContainer, get_container
from src.domain.enums import MediaType
from src.schemas.discover import (
    AddRequestPayload,
    AddRequestResponse,
    MediaSearchResponse,
    MediaSearchResult,
    RootFolder,
    RootFoldersResponse,
    SeasonOption,
    SeriesSeasonsResponse,
)
from src.schemas.requests import MediaRequest, MovieRequest, SeriesRequest

router = APIRouter(prefix="/discover", tags=["Discover"], dependencies=[Depends(require_api_key)])


def _get_container() -> AppContainer:
    return get_container()


def _search_use_case(container: AppContainer = Depends(_get_container)) -> SearchMediaUseCase:
    return container.use_cases.discover.search


def _season_options_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListSeasonOptionsUseCase:
    return container.use_cases.discover.season_options


def _root_folders_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListRootFoldersUseCase:
    return container.use_cases.discover.root_folders


def _add_request_use_case(
    container: AppContainer = Depends(_get_container),
) -> AddMediaRequestUseCase:
    return container.use_cases.discover.add_request


_SERVER_ERROR = "Unexpected server error."
_UPSTREAM_ERROR = "Sonarr, Radarr or the metadata provider could not be reached."

SEARCH_RESPONSES = error_responses(
    {
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Invalid search parameters.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_503_SERVICE_UNAVAILABLE: "The metadata provider is not configured.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

SEASONS_RESPONSES = error_responses(
    {
        status.HTTP_404_NOT_FOUND: "No series matches the TVDB id.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

ROOT_FOLDERS_RESPONSES = error_responses(
    {
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Invalid media type.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

ADD_REQUEST_RESPONSES = error_responses(
    {
        status.HTTP_400_BAD_REQUEST: "Invalid root folder, season selection or quality profile.",
        status.HTTP_404_NOT_FOUND: "No media matches the provider id.",
        status.HTTP_422_UNPROCESSABLE_CONTENT: "Validation failed for the provided fields.",
        status.HTTP_502_BAD_GATEWAY: _UPSTREAM_ERROR,
        status.HTTP_500_INTERNAL_SERVER_ERROR: _SERVER_ERROR,
    }
)

TvdbIdParam = Annotated[int, Path(..., alias="tvdbId", ge=1)]


@router.get("/search", response_model=MediaSearchResponse, responses=SEARCH_RESPONSES)
async def search_media(
    search_use_case: SearchMediaUseCase = Depends(_search_use_case),
    query: str = Query(..., alias="q", min_length=1),
    media_type: MediaType | None = Query(
        None,
        alias="type",
        description="Restrict the search to one media type. Both are searched when omitted.",
    ),
    language: str | None = Query(
        None,
        alias="lang",
        min_length=2,
        max_length=8,
        description=(
            "Preferred language for the titles and overviews, as a 2- or 3-letter code. "
            "Falls back to the configured metadata languages."
        ),
    ),
) -> MediaSearchResponse:
    results = await search_use_case.execute(query, media_type, language)
    return MediaSearchResponse(results=[_search_result_to_schema(result) for result in results])


@router.get(
    "/series/{tvdbId}/seasons",
    response_model=SeriesSeasonsResponse,
    responses=SEASONS_RESPONSES,
)
async def list_series_seasons(
    tvdb_id: TvdbIdParam,
    season_options_use_case: ListSeasonOptionsUseCase = Depends(_season_options_use_case),
) -> SeriesSeasonsResponse:
    seasons = await season_options_use_case.execute(tvdb_id)
    return _seasons_to_schema(seasons)


@router.get("/root-folders", response_model=RootFoldersResponse, responses=ROOT_FOLDERS_RESPONSES)
async def list_root_folders(
    root_folders_use_case: ListRootFoldersUseCase = Depends(_root_folders_use_case),
    media_type: MediaType = Query(..., alias="type"),
) -> RootFoldersResponse:
    folders = await root_folders_use_case.execute(media_type)
    return RootFoldersResponse(
        folders=[RootFolder(path=folder.path, free_space=folder.free_space) for folder in folders]
    )


@router.post(
    "/requests",
    response_model=AddRequestResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ADD_REQUEST_RESPONSES,
)
async def add_request(
    payload: AddRequestPayload,
    add_request_use_case: AddMediaRequestUseCase = Depends(_add_request_use_case),
) -> AddRequestResponse:
    command = AddMediaRequestCommand(
        media_type=MediaType(payload.type),
        provider_id=payload.provider_id,
        root_folder_path=payload.root_folder_path,
        season_numbers=list(payload.season_numbers or []),
    )
    requests = await add_request_use_case.execute(command)
    return AddRequestResponse(requests=[_dto_to_schema(dto) for dto in requests])


def _search_result_to_schema(dto: MediaSearchResultDTO) -> MediaSearchResult:
    return MediaSearchResult(
        type=dto.media_type,
        provider_id=dto.provider_id,
        title=dto.title,
        year=dto.year,
        overview=dto.overview,
        poster_url=dto.poster_url,
        in_library=dto.in_library,
        library_id=dto.library_id,
        requested_seasons=dto.requested_seasons,
        request_id=dto.request_id,
        request_status=dto.request_status,
    )


def _seasons_to_schema(dto: SeriesSeasonsDTO) -> SeriesSeasonsResponse:
    return SeriesSeasonsResponse(
        tvdb_id=dto.tvdb_id,
        in_library=dto.in_library,
        library_id=dto.library_id,
        seasons=[
            SeasonOption(
                season_number=season.season_number,
                monitored=season.monitored,
                requested=season.requested,
                request_id=season.request_id,
            )
            for season in dto.seasons
        ],
    )


def _dto_to_schema(dto: MediaRequestDTO) -> MediaRequest:
    if isinstance(dto, MovieRequestDTO):
        return MovieRequest.model_validate(dto)
    if isinstance(dto, SeriesRequestDTO):
        return SeriesRequest.model_validate(dto)
    raise TypeError("Unsupported DTO type")


__all__ = ["router"]
