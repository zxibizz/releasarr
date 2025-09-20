import asyncio
from datetime import datetime

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.migrator import run_migrations
from app.db.session import AsyncSessionLocal
from app.models import MediaRequest, Release, RequestStatus, RequestType


async def init_db(with_sample_data: bool = True) -> None:
    settings = get_settings()
    await run_migrations(settings.database_url)

    if not with_sample_data:
        return

    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(func.count(MediaRequest.id)))
        if existing:
            return

        request = MediaRequest(
            type=RequestType.MOVIE,
            title="Example Movie",
            year=2024,
            overview="Demo request created by init_db",
            status=RequestStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(request)
        await session.flush()

        release = Release(
            name="Example Release",
            size=0,
            status="pending",
            added_date=datetime.utcnow(),
            torrent_source="mock",
        )
        release.requests.append(request)
        session.add(release)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(init_db())
