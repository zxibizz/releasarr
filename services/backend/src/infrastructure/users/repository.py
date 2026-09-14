"""SQLAlchemy-backed user repository implementation."""

from __future__ import annotations

from dataclasses import dataclass, fields

from sqlalchemy import func, select

from src.application.interfaces.users import (
    CreateUserData,
    UpdateUserData,
    UserRecord,
    UserRepository,
)
from src.application.utility.sentinels import UNSET
from src.db.repository import BaseSqlAlchemyRepository
from src.domain import models


@dataclass(slots=True)
class SqlAlchemyUserRepository(BaseSqlAlchemyRepository, UserRepository):
    """Persist user accounts using SQLAlchemy sessions."""

    async def list_users(self) -> list[UserRecord]:
        async with self.db.session() as session:
            stmt = select(models.User).order_by(models.User.username)
            result = await session.execute(stmt)
            return [self._to_record(user) for user in result.scalars().all()]

    async def count_users(self) -> int:
        async with self.db.session() as session:
            result = await session.execute(select(func.count(models.User.id)))
            return int(result.scalar() or 0)

    async def get_user(self, user_id: str) -> UserRecord | None:
        async with self.db.session() as session:
            user = await session.get(models.User, user_id)
            return self._to_record(user) if user is not None else None

    async def get_by_username(self, username: str) -> UserRecord | None:
        async with self.db.session() as session:
            stmt = select(models.User).where(models.User.username == username.lower())
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return self._to_record(user) if user is not None else None

    async def create_user(self, data: CreateUserData) -> UserRecord:
        async with self.db.transaction() as session:
            user = models.User(
                id=data.id,
                username=data.username.lower(),
                display_name=data.display_name,
                password_hash=data.password_hash,
                role=data.role,
                is_active=data.is_active,
                can_view_all_requests=data.can_view_all_requests,
                can_access_tasks=data.can_access_tasks,
                can_access_indexers=data.can_access_indexers,
                can_access_logs=data.can_access_logs,
                allowed_root_folders=list(data.allowed_root_folders),
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return self._to_record(user)

    async def update_user(self, user_id: str, data: UpdateUserData) -> UserRecord | None:
        async with self.db.transaction() as session:
            user = await session.get(models.User, user_id)
            if user is None:
                return None

            for field in fields(UpdateUserData):
                value = getattr(data, field.name)
                if value is UNSET:
                    continue
                setattr(user, field.name, value)

            await session.flush()
            await session.refresh(user)
            return self._to_record(user)

    async def delete_user(self, user_id: str) -> bool:
        async with self.db.transaction() as session:
            user = await session.get(models.User, user_id)
            if user is None:
                return False
            await session.delete(user)
            return True

    @staticmethod
    def _to_record(user: models.User) -> UserRecord:
        return UserRecord(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
            can_view_all_requests=user.can_view_all_requests,
            can_access_tasks=user.can_access_tasks,
            can_access_indexers=user.can_access_indexers,
            can_access_logs=user.can_access_logs,
            allowed_root_folders=list(user.allowed_root_folders),
            failed_login_attempts=user.failed_login_attempts,
            locked_until=user.locked_until,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


__all__ = ["SqlAlchemyUserRepository"]
