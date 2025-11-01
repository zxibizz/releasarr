from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_release_service
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.torrents import DownloadTorrentRequest, TorrentSearchResponse
from app.services.releases import ReleaseService
from app.services.torrents import TorrentService

router = APIRouter(prefix="/torrents", tags=["torrents"])


@router.get("/search", response_model=TorrentSearchResponse)
async def search_torrents(
    q: str = Query(..., min_length=1, alias="q"),
) -> TorrentSearchResponse:
    service = TorrentService()
    return await service.search(q)


@router.post("/download", status_code=202)
async def download_torrent(
    payload: DownloadTorrentRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    release_service = ReleaseService(session)
    clients = release_service.clients
    if not (clients.prowlarr.enabled and clients.qbittorrent.enabled):
        raise HTTPException(status_code=503, detail="Torrent download service unavailable")
    release = await release_service.create_release(
        name=f"Request {payload.request_id} download",
        request_ids=[payload.request_id],
    )
    ok = await release_service.attach_torrent(release.id, payload.torrent_link)
    if not ok:
        raise HTTPException(status_code=404, detail="Failed to queue download")
    return {"message": "Download queued", "release_id": release.id}
