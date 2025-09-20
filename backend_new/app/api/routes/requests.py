from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models import RequestStatus, RequestType
from app.schemas.common import Release
from app.schemas.requests import (
    MediaRequestSchema,
    NewMediaRequest,
    RequestsResponse,
    UpdateMediaRequest,
)
from app.services.releases import ReleaseService
from app.services.requests import RequestService

router = APIRouter(prefix="/requests", tags=["requests"])


@router.get("", response_model=RequestsResponse)
async def list_requests(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: RequestStatus | None = Query(default=None),
    type_: RequestType | None = Query(default=None, alias="type"),
    session: AsyncSession = Depends(get_db),
) -> RequestsResponse:
    service = RequestService(session)
    return await service.list_requests(page=page, per_page=per_page, status=status, type_=type_)


@router.post("", response_model=MediaRequestSchema, status_code=201)
async def create_request(
    payload: NewMediaRequest,
    session: AsyncSession = Depends(get_db),
) -> MediaRequestSchema:
    service = RequestService(session)
    return await service.create_request(payload)


@router.get("/{request_id}", response_model=MediaRequestSchema)
async def get_request(
    request_id: int,
    session: AsyncSession = Depends(get_db),
) -> MediaRequestSchema:
    service = RequestService(session)
    result = await service.get_request(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Request not found")
    return result


@router.put("/{request_id}", response_model=MediaRequestSchema)
async def update_request(
    request_id: int,
    payload: UpdateMediaRequest,
    session: AsyncSession = Depends(get_db),
) -> MediaRequestSchema:
    service = RequestService(session)
    result = await service.update_request(request_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Request not found")
    return result


@router.delete("/{request_id}", status_code=204)
async def delete_request(
    request_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    service = RequestService(session)
    deleted = await service.delete_request(request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Request not found")


@router.get("/{request_id}/releases", response_model=list[Release])
async def get_request_releases(
    request_id: int,
    session: AsyncSession = Depends(get_db),
) -> list[Release]:
    request_service = RequestService(session)
    request_instance = await request_service.get_request(request_id)
    if not request_instance:
        raise HTTPException(status_code=404, detail="Request not found")
    release_service = ReleaseService(session)
    return await release_service.get_request_releases(request_id)
