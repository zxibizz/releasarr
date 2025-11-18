from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.common import Release
from app.schemas.releases import NewRelease, SuccessResponse, UpdateFileMapping
from app.services.releases import ReleaseService

router = APIRouter(prefix="/releases", tags=["releases"])


@router.get("", response_model=list[Release])
async def list_releases(
    status: str | None = Query(default=None),
    request_id: int | None = Query(default=None, alias="request_id"),
    session: AsyncSession = Depends(get_db),
) -> list[Release]:
    service = ReleaseService(session)
    return await service.list_releases(status=status, request_id=request_id)


@router.post("", response_model=Release, status_code=201)
async def create_release(
    payload: NewRelease,
    session: AsyncSession = Depends(get_db),
) -> Release:
    name = payload.name or "Manual Release"
    request_ids = payload.request_ids
    size = payload.size or 0
    torrent_source = payload.torrent_source
    quality = payload.quality
    service = ReleaseService(session)
    return await service.create_release(
        name=name,
        request_ids=request_ids,
        size=size,
        torrent_source=torrent_source,
        quality=quality,
    )


@router.get("/{release_id}", response_model=Release)
async def get_release(
    release_id: int,
    session: AsyncSession = Depends(get_db),
) -> Release:
    service = ReleaseService(session)
    release = await service.get_release(release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    return release


@router.delete("/{release_id}", status_code=204)
async def delete_release(
    release_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    service = ReleaseService(session)
    deleted = await service.delete_release(release_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Release not found")


@router.post("/{release_id}/pause", status_code=202)
async def pause_release(
    release_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    service = ReleaseService(session)
    ok = await service.pause_release(release_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Release not found")


@router.post("/{release_id}/resume", status_code=202)
async def resume_release(
    release_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    service = ReleaseService(session)
    ok = await service.resume_release(release_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Release not found")


@router.put("/{release_id}/files/{file_id}/mapping", response_model=SuccessResponse)
async def update_file_mapping(
    release_id: int,
    file_id: int,
    payload: UpdateFileMapping,
    session: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    service = ReleaseService(session)
    result = await service.update_file_mapping(release_id, file_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Release or file not found")
    return result
