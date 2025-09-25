"""FastAPI routes for release management operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from src.api.dependencies import require_api_key
from src.api.errors import api_error
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
    ReleaseFileNotFoundError,
    ReleaseNotFoundError,
)
from src.application.use_cases.releases.get_release import GetReleaseUseCase
from src.application.use_cases.releases.list_releases import ListReleasesUseCase
from src.application.use_cases.releases.pause_release import PauseReleaseUseCase
from src.application.use_cases.releases.queue_release_download import QueueReleaseDownloadUseCase
from src.application.use_cases.releases.resume_release import ResumeReleaseUseCase
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


def _release_repository(container: AppContainer) -> object:
    return container.repositories.releases


def _list_use_case(container: AppContainer = Depends(_get_container)) -> ListReleasesUseCase:
    repository = _release_repository(container)
    return ListReleasesUseCase(repository=repository, settings=container.settings)


def _create_use_case(container: AppContainer = Depends(_get_container)) -> CreateReleaseUseCase:
    repository = _release_repository(container)
    return CreateReleaseUseCase(repository=repository)


def _get_use_case(container: AppContainer = Depends(_get_container)) -> GetReleaseUseCase:
    repository = _release_repository(container)
    return GetReleaseUseCase(repository=repository)


def _delete_use_case(container: AppContainer = Depends(_get_container)) -> DeleteReleaseUseCase:
    repository = _release_repository(container)
    return DeleteReleaseUseCase(repository=repository)


def _update_mappings_use_case(
    container: AppContainer = Depends(_get_container),
) -> UpdateReleaseFileMappingsUseCase:
    repository = _release_repository(container)
    return UpdateReleaseFileMappingsUseCase(repository=repository)


def _pause_use_case(container: AppContainer = Depends(_get_container)) -> PauseReleaseUseCase:
    repository = _release_repository(container)
    lifecycle = container.services.release_lifecycle
    return PauseReleaseUseCase(repository=repository, lifecycle_service=lifecycle)


def _resume_use_case(container: AppContainer = Depends(_get_container)) -> ResumeReleaseUseCase:
    repository = _release_repository(container)
    lifecycle = container.services.release_lifecycle
    return ResumeReleaseUseCase(repository=repository, lifecycle_service=lifecycle)


def _search_use_case(
    container: AppContainer = Depends(_get_container),
) -> ReleaseSearchSourcesUseCase:
    search_service = container.services.release_search
    return ReleaseSearchSourcesUseCase(search_service=search_service)


def _queue_download_use_case(
    container: AppContainer = Depends(_get_container),
) -> QueueReleaseDownloadUseCase:
    repository = _release_repository(container)
    download_service = container.services.release_download
    return QueueReleaseDownloadUseCase(repository=repository, download_service=download_service)


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


@router.get("", response_model=ReleasesResponse)
async def list_releases(
    list_use_case: ListReleasesUseCase = Depends(_list_use_case),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    request_id: str | None = Query(default=None, alias="request_id"),
) -> ReleasesResponse:
    status_value: ReleaseStatus | None = None
    if status_filter:
        try:
            status_value = ReleaseStatus(status_filter)
        except ValueError as exc:  # pragma: no cover
            raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_status_filter", str(exc)) from exc

    options = ListReleasesOptions(
        page=page,
        per_page=per_page,
        status=status_value,
        request_id=request_id,
    )
    page_dto = await list_use_case.execute(options)
    return _page_to_response(page_dto)


@router.get("/search", response_model=ReleaseSearchResponse)
async def search_releases(
    q: str = Query(...),
    request_id: str | None = Query(default=None, alias="request_id"),
    search_use_case: ReleaseSearchSourcesUseCase = Depends(_search_use_case),
) -> ReleaseSearchResponse:
    command = SearchReleaseSourcesCommand(query=q, request_id=request_id)
    dto = await search_use_case.execute(command)
    return _search_to_response(dto)


@router.post("", response_model=Release, status_code=status.HTTP_201_CREATED)
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


@router.get("/{release_id}", response_model=Release)
async def get_release(
    release_id: str,
    get_use_case: GetReleaseUseCase = Depends(_get_use_case),
) -> Release:
    try:
        dto = await get_use_case.execute(release_id)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    return _dto_to_release(dto)


@router.delete("/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_release(
    release_id: str,
    delete_use_case: DeleteReleaseUseCase = Depends(_delete_use_case),
) -> Response:
    try:
        await delete_use_case.execute(release_id)
    except ReleaseNotFoundError as exc:
        raise api_error(status.HTTP_404_NOT_FOUND, "release_not_found", str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{release_id}/pause",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def pause_release(
    release_id: str,
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
    "/{release_id}/resume",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resume_release(
    release_id: str,
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


@router.put("/{release_id}/files/mapping", response_model=SuccessResponse)
async def update_file_mappings(
    release_id: str,
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
    "/{request_id}/releases/download",
    response_model=AsyncOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def queue_release_download(
    request_id: str,
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
    if dto.location:
        response.headers["Location"] = dto.location
    return _async_to_response(dto)


__all__ = ["request_releases_router", "router"]
