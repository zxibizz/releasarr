"""FastAPI routes for release management operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from src.api.dependencies import require_api_key
from src.api.errors import api_error
from src.api.responses import error_response
from src.application.use_cases.releases.commands import (
    CreateReleaseCommand,
    FileMappingCommand,
    ListReleasesOptions,
    QueueReleaseDownloadCommand,
    SearchReleaseSourcesCommand,
    UpdateFileMappingsCommand,
)
from src.application.use_cases.releases.create_release import CreateReleaseUseCase
from src.application.use_cases.releases.delete_release import DeleteReleaseUseCase
from src.application.use_cases.releases.dto import (
    AsyncOperationDTO,
    ReleaseDTO,
    ReleaseSearchResponseDTO,
    ReleasesPageDTO,
)
from src.application.use_cases.releases.exceptions import (
    ReleaseActionNotAllowedError,
    ReleaseConflictError,
    ReleaseDownloadConflictError,
    ReleaseDownloadFailedError,
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.application.use_cases.releases.get_release import GetReleaseUseCase
from src.application.use_cases.releases.list_releases import ListReleasesUseCase
from src.application.use_cases.releases.pause_release import PauseReleaseUseCase
from src.application.use_cases.releases.queue_release_download import QueueReleaseDownloadUseCase
from src.application.use_cases.releases.resume_release import ResumeReleaseUseCase
from src.application.use_cases.releases.search_release_sources import SearchReleaseSourcesUseCase
from src.application.use_cases.releases.update_file_mappings import UpdateReleaseFileMappingsUseCase
from src.core.container import AppContainer, get_container
from src.domain.enums import MediaType, ReleaseStatus
from src.schemas.common import SuccessResponse
from src.schemas.enums import AsyncJobStatus
from src.schemas.jobs import AsyncOperationResponse
from src.schemas.releases import (
    AddReleaseRequest,
    FileRequestMapping,
    Release,
    ReleaseDownloadRequest,
    ReleaseFile,
    ReleaseFileMappingsUpdate,
    ReleaseSearchResponse,
    ReleaseSearchResult,
    ReleasesResponse,
)

router = APIRouter(prefix="/releases", tags=["Releases"], dependencies=[Depends(require_api_key)])
request_releases_router = APIRouter(
    prefix="/requests", tags=["Releases"], dependencies=[Depends(require_api_key)]
)


def _get_container() -> AppContainer:
    return get_container()


def _list_use_case(container: AppContainer = Depends(_get_container)) -> ListReleasesUseCase:
    return container.use_cases.releases.list


def _create_use_case(container: AppContainer = Depends(_get_container)) -> CreateReleaseUseCase:
    return container.use_cases.releases.create


def _get_use_case(container: AppContainer = Depends(_get_container)) -> GetReleaseUseCase:
    return container.use_cases.releases.get


def _delete_use_case(container: AppContainer = Depends(_get_container)) -> DeleteReleaseUseCase:
    return container.use_cases.releases.delete


def _update_mappings_use_case(
    container: AppContainer = Depends(_get_container),
) -> UpdateReleaseFileMappingsUseCase:
    return container.use_cases.releases.update_mappings


def _pause_use_case(container: AppContainer = Depends(_get_container)) -> PauseReleaseUseCase:
    return container.use_cases.releases.pause


def _resume_use_case(container: AppContainer = Depends(_get_container)) -> ResumeReleaseUseCase:
    return container.use_cases.releases.resume


def _search_use_case(
    container: AppContainer = Depends(_get_container),
) -> SearchReleaseSourcesUseCase:
    return container.use_cases.releases.search_sources


def _queue_download_use_case(
    container: AppContainer = Depends(_get_container),
) -> QueueReleaseDownloadUseCase:
    return container.use_cases.releases.queue_download


RELEASE_LIST_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response(
        "Invalid pagination or filter parameters."
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

CREATE_RELEASE_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response("Malformed request payload."),
    status.HTTP_409_CONFLICT: error_response(
        "A release with the same identifier already exists."
    ),
    status.HTTP_422_UNPROCESSABLE_CONTENT: error_response(
        "Validation failed for the provided fields."
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

GET_RELEASE_RESPONSES = {
    status.HTTP_404_NOT_FOUND: error_response("Release not found."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

DELETE_RELEASE_RESPONSES = {
    status.HTTP_404_NOT_FOUND: error_response("Release not found."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

PAUSE_RELEASE_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response(
        "Release cannot be paused because the request was invalid."
    ),
    status.HTTP_404_NOT_FOUND: error_response("Release not found."),
    status.HTTP_409_CONFLICT: error_response("Release is not in a pausable state."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

RESUME_RELEASE_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response(
        "Release cannot be resumed because the request was invalid."
    ),
    status.HTTP_404_NOT_FOUND: error_response("Release not found."),
    status.HTTP_409_CONFLICT: error_response("Release is not in a resumable state."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

UPDATE_MAPPINGS_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response("Malformed request payload."),
    status.HTTP_404_NOT_FOUND: error_response("Release or file not found."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

SEARCH_RELEASES_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response("Malformed search query."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

REQUEST_RELEASES_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response(
        "Invalid pagination or filter parameters."
    ),
    status.HTTP_404_NOT_FOUND: error_response("Request not found."),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}

QUEUE_DOWNLOAD_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: error_response("Malformed request body."),
    status.HTTP_404_NOT_FOUND: error_response(
        "Release candidate not found for the request."
    ),
    status.HTTP_409_CONFLICT: error_response(
        "Request already has an active download."
    ),
    status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
        "Unexpected server error."
    ),
}


ReleaseIdParam = Annotated[str, Path(..., alias="releaseId")]
RequestIdParam = Annotated[str, Path(..., alias="requestId")]


def _parse_status(status_filter: str | None) -> ReleaseStatus | None:
    if not status_filter:
        return None
    try:
        return ReleaseStatus(status_filter)
    except ValueError as exc:  # pragma: no cover - defensive
        raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_status_filter", str(exc)) from exc


def _dto_to_release(dto: ReleaseDTO) -> Release:
    return Release(
        id=dto.id,
        name=dto.name,
        hash=dto.info_hash,
        size=dto.size_bytes,
        files=[_dto_to_file(file_dto) for file_dto in dto.files],
        status=dto.status,
        progress=dto.progress,
        download_speed=dto.download_speed,
        upload_speed=dto.upload_speed,
        seeders=dto.seeders,
        leechers=dto.leechers,
        ratio=dto.ratio,
        added_date=dto.added_at,
        completed_date=dto.completed_at,
        request_ids=list(dto.request_ids),
        torrent_source=dto.torrent_source,
        quality=dto.quality,
    )


def _dto_to_file(file_dto) -> ReleaseFile:
    return ReleaseFile(
        id=file_dto.id,
        name=file_dto.name,
        size=file_dto.size_bytes,
        path=file_dto.path,
        request_mapping=_dto_to_file_mapping(file_dto.request_mapping),
    )


def _dto_to_file_mapping(mapping) -> FileRequestMapping | None:
    if mapping is None or mapping.mapping_type is None:
        return None

    media_type = MediaType(mapping.mapping_type)
    if media_type is MediaType.MOVIE:
        from src.schemas.releases import MovieFileRequestMapping

        return MovieFileRequestMapping(
            mapping_type=media_type.value,
            request_id=mapping.request_id or "",
            request_title=mapping.request_title,
        )

    from src.schemas.releases import SeriesFileRequestMapping

    return SeriesFileRequestMapping(
        mapping_type=media_type.value,
        request_id=mapping.request_id or "",
        request_title=mapping.request_title,
        season=mapping.season or 0,
        episode=mapping.episode or 0,
    )


def _page_to_response(page: ReleasesPageDTO) -> ReleasesResponse:
    releases = [_dto_to_release(dto) for dto in page.releases]
    return ReleasesResponse(
        releases=releases, total=page.total, page=page.page, per_page=page.per_page
    )


def _async_to_response(dto: AsyncOperationDTO) -> AsyncOperationResponse:
    try:
        status_enum = AsyncJobStatus(dto.status)
    except ValueError:
        status_enum = AsyncJobStatus.PENDING
    return AsyncOperationResponse(
        operation=dto.operation,
        status=status_enum,
        operation_id=dto.operation_id,
        location=dto.location,
        message=dto.message,
        resource_id=dto.resource_id,
        details=dto.details,
    )


def _search_to_response(dto: ReleaseSearchResponseDTO) -> ReleaseSearchResponse:
    results = [
        ReleaseSearchResult(
            release_id=result.release_id,
            release_name=result.release_name,
            size=result.size,
            magnet_link=result.magnet_link,
            torrent_file_url=result.torrent_file_url,
            info_url=result.info_url,
            seeders=result.seeders,
            leechers=result.leechers,
            quality=result.quality,
            source=result.source,
            request_id=result.request_id,
        )
        for result in dto.results
    ]
    return ReleaseSearchResponse(results=results, query=dto.query, total_results=dto.total_results)


@router.get("", response_model=ReleasesResponse, responses=RELEASE_LIST_RESPONSES)
async def list_releases(
    list_use_case: ListReleasesUseCase = Depends(_list_use_case),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    request_id: str | None = Query(default=None, alias="request_id"),
) -> ReleasesResponse:
    status_value = _parse_status(status_filter)

    options = ListReleasesOptions(
        page=page,
        per_page=per_page,
        status=status_value,
        request_id=request_id,
    )
    page_dto = await list_use_case.execute(options)
    return _page_to_response(page_dto)


@router.get("/search", response_model=ReleaseSearchResponse, responses=SEARCH_RELEASES_RESPONSES)
async def search_releases(
    q: str = Query(...),
    request_id: str | None = Query(default=None, alias="request_id"),
    search_use_case: SearchReleaseSourcesUseCase = Depends(_search_use_case),
) -> ReleaseSearchResponse:
    command = SearchReleaseSourcesCommand(query=q, request_id=request_id)
    dto = await search_use_case.execute(command)
    return _search_to_response(dto)


@request_releases_router.get(
    "/{requestId}/releases",
    response_model=ReleasesResponse,
    responses=REQUEST_RELEASES_RESPONSES,
    deprecated=True,
)
async def list_releases_for_request(
    request_id: RequestIdParam,
    list_use_case: ListReleasesUseCase = Depends(_list_use_case),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
) -> ReleasesResponse:
    status_value = _parse_status(status_filter)
    options = ListReleasesOptions(
        page=page,
        per_page=per_page,
        status=status_value,
        request_id=request_id,
    )
    page_dto = await list_use_case.execute(options)
    return _page_to_response(page_dto)


@router.post(
    "",
    response_model=Release,
    status_code=status.HTTP_201_CREATED,
    responses=CREATE_RELEASE_RESPONSES,
)
async def create_release(
    payload: AddReleaseRequest,
    create_use_case: CreateReleaseUseCase = Depends(_create_use_case),
) -> Release:
    command = CreateReleaseCommand(
        magnet_link=payload.magnet_link, request_ids=list(payload.request_ids)
    )
    try:
        dto = await create_use_case.execute(command)
    except ReleaseConflictError as exc:
        raise api_error(status.HTTP_409_CONFLICT, "release_conflict", str(exc)) from exc
    except ValueError as exc:
        raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_release", str(exc)) from exc
    return _dto_to_release(dto)


@router.get(
    "/{releaseId}",
    response_model=Release,
    responses=GET_RELEASE_RESPONSES,
)
async def get_release(
    release_id: ReleaseIdParam,
    get_use_case: GetReleaseUseCase = Depends(_get_use_case),
) -> Release:
    try:
        dto = await get_use_case.execute(release_id)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    return _dto_to_release(dto)


@router.delete(
    "/{releaseId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=DELETE_RELEASE_RESPONSES,
)
async def delete_release(
    release_id: ReleaseIdParam,
    delete_use_case: DeleteReleaseUseCase = Depends(_delete_use_case),
) -> Response:
    try:
        await delete_use_case.execute(release_id)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{releaseId}/pause",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=PAUSE_RELEASE_RESPONSES,
)
async def pause_release(
    release_id: ReleaseIdParam,
    response: Response,
    pause_use_case: PauseReleaseUseCase = Depends(_pause_use_case),
) -> AsyncOperationResponse:
    try:
        dto = await pause_use_case.execute(release_id)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    except ReleaseActionNotAllowedError as exc:
        raise api_error(status.HTTP_409_CONFLICT, "release_action_conflict", str(exc)) from exc
    if dto.location:
        response.headers["Location"] = dto.location
    return _async_to_response(dto)


@router.post(
    "/{releaseId}/resume",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=RESUME_RELEASE_RESPONSES,
)
async def resume_release(
    release_id: ReleaseIdParam,
    response: Response,
    resume_use_case: ResumeReleaseUseCase = Depends(_resume_use_case),
) -> AsyncOperationResponse:
    try:
        dto = await resume_use_case.execute(release_id)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    except ReleaseActionNotAllowedError as exc:
        raise api_error(status.HTTP_409_CONFLICT, "release_action_conflict", str(exc)) from exc
    if dto.location:
        response.headers["Location"] = dto.location
    return _async_to_response(dto)


@router.put(
    "/{releaseId}/files/mapping",
    response_model=SuccessResponse,
    responses=UPDATE_MAPPINGS_RESPONSES,
)
async def update_file_mappings(
    release_id: ReleaseIdParam,
    payload: ReleaseFileMappingsUpdate,
    update_use_case: UpdateReleaseFileMappingsUseCase = Depends(_update_mappings_use_case),
) -> SuccessResponse:
    command = _build_update_command(release_id, payload)
    try:
        await update_use_case.execute(command)
    except ReleaseFileNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_file_not_found", str(exc)) from exc
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    except ValueError as exc:
        raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_mapping", str(exc)) from exc
    return SuccessResponse()


def _build_update_command(
    release_id: str, payload: ReleaseFileMappingsUpdate
) -> UpdateFileMappingsCommand:
    commands: list[FileMappingCommand] = []
    for file_input in payload.files:
        mapping = file_input.request_mapping
        mapping_type = mapping.mapping_type if mapping else None
        commands.append(
            FileMappingCommand(
                file_id=file_input.file_id,
                mapping_type=mapping_type,
                request_id=mapping.request_id if mapping else None,
                request_title=mapping.request_title if mapping else None,
                season=getattr(mapping, "season", None),
                episode=getattr(mapping, "episode", None),
            )
        )
    return UpdateFileMappingsCommand(release_id=release_id, files=commands)


@request_releases_router.post(
    "/{requestId}/releases/download",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=QUEUE_DOWNLOAD_RESPONSES,
)
async def queue_release_download(
    request_id: RequestIdParam,
    payload: ReleaseDownloadRequest,
    response: Response,
    queue_use_case: QueueReleaseDownloadUseCase = Depends(_queue_download_use_case),
) -> AsyncOperationResponse:
    command = QueueReleaseDownloadCommand(request_id=request_id, release_id=payload.release_id)
    try:
        dto = await queue_use_case.execute(command)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    except ReleaseDownloadConflictError as exc:
        raise api_error(status.HTTP_409_CONFLICT, "release_download_conflict", str(exc)) from exc
    except ReleaseDownloadFailedError as exc:
        raise api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, "release_download_failed", str(exc)) from exc
    if dto.location:
        response.headers["Location"] = dto.location
    return _async_to_response(dto)


__all__ = ["request_releases_router", "router"]
