from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.application.interfaces.releases_repository import I_ReleasesRepository
from src.application.models import Release, ReleaseFileMatching, Show


class ReleasesRepository(I_ReleasesRepository):
    async def create(self, db_session: AsyncSession, release: Release) -> None:
        db_session.add(release)

    async def update(self, db_session: AsyncSession, release: Release) -> None:
        db_session.add(release)

    async def get(self, db_session: AsyncSession, name: str) -> Release | None:
        return await db_session.scalar(
            select(Release)
            .where(Release.name == name)
            .options(joinedload(Release.file_matchings))
        )

    async def update_file_matchings(
        self, db_session: AsyncSession, file_matchings: list[ReleaseFileMatching]
    ) -> None:
        db_session.add_all(file_matchings)

    async def get_by_torrent_hashes(
        self, db_session: AsyncSession, torrent_hashes: list[str]
    ) -> list[Release]:
        return await db_session.scalars(
            select(Release).where(Release.qbittorrent_guid.in_(torrent_hashes))
        )

    async def get_finished_not_uploaded(
        self, db_session: AsyncSession
    ) -> list[Release]:
        res = await db_session.scalars(
            select(Release)
            .where(
                Release.torrent_is_finished.is_(True),
                (
                    (Release.qbittorrent_guid != Release.last_exported_torrent_guid)
                    | Release.last_exported_torrent_guid.is_(None)
                ),
                Release.export_failures_count < 5,
            )
            .options(joinedload(Release.file_matchings), joinedload(Release.show))
        )
        return res.unique()

    async def get_outdated_releases(self, db_session: AsyncSession) -> list[Release]:
        missing_shows: list[Show] = (
            await db_session.scalars(
                select(Show)
                .options(
                    joinedload(Show.releases).options(
                        joinedload(Release.file_matchings),
                    ),
                )
                .where(Show.is_missing)
            )
        ).unique()
        res = []
        for missing_show in missing_shows:
            for release in missing_show.releases:
                for matching in release.file_matchings:
                    if matching.season_number in missing_show.missing_seasons:
                        res.append(release)
                        break

        return res

    async def delete(self, db_session, name):
        release = await db_session.scalar(select(Release).where(Release.name == name))
        await db_session.execute(
            delete(ReleaseFileMatching).where(ReleaseFileMatching.release == release)
        )
        await db_session.delete(release)
