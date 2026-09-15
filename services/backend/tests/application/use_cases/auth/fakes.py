"""In-memory fakes for the auth repositories, used by application-layer tests."""

from __future__ import annotations

from dataclasses import fields

from src.application.interfaces.auth import RefreshTokenRecord, ServiceApiKeyRecord
from src.application.interfaces.users import CreateUserData, UpdateUserData, UserRecord
from src.application.utility.sentinels import UNSET
from src.domain.models import utc_now


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[str, UserRecord] = {}

    async def list_users(self) -> list[UserRecord]:
        return sorted(self.users.values(), key=lambda user: user.username)

    async def count_users(self) -> int:
        return len(self.users)

    async def get_user(self, user_id: str) -> UserRecord | None:
        return self.users.get(user_id)

    async def get_by_username(self, username: str) -> UserRecord | None:
        for user in self.users.values():
            if user.username == username.lower():
                return user
        return None

    async def create_user(self, data: CreateUserData) -> UserRecord:
        now = utc_now()
        user = UserRecord(
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
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
        self.users[user.id] = user
        return user

    async def update_user(self, user_id: str, data: UpdateUserData) -> UserRecord | None:
        user = self.users.get(user_id)
        if user is None:
            return None
        for field in fields(UpdateUserData):
            value = getattr(data, field.name)
            if value is not UNSET:
                setattr(user, field.name, value)
        return user

    async def delete_user(self, user_id: str) -> bool:
        return self.users.pop(user_id, None) is not None


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self.tokens: dict[str, RefreshTokenRecord] = {}

    async def store(
        self,
        *,
        id: str,
        user_id: str,
        family_id: str,
        token_hash: str,
        remember: bool,
        issued_at,
        expires_at,
    ) -> RefreshTokenRecord:
        record = RefreshTokenRecord(
            id=id,
            user_id=user_id,
            family_id=family_id,
            token_hash=token_hash,
            remember=remember,
            issued_at=issued_at,
            expires_at=expires_at,
            revoked_at=None,
        )
        self.tokens[id] = record
        return record

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        for record in self.tokens.values():
            if record.token_hash == token_hash:
                return record
        return None

    async def revoke(self, token_id: str) -> None:
        record = self.tokens.get(token_id)
        if record is not None and record.revoked_at is None:
            record.revoked_at = utc_now()

    async def revoke_family(self, family_id: str) -> None:
        now = utc_now()
        for record in self.tokens.values():
            if record.family_id == family_id and record.revoked_at is None:
                record.revoked_at = now

    async def has_live_token(self, family_id: str, *, now) -> bool:
        return any(
            record.family_id == family_id and record.revoked_at is None and record.expires_at > now
            for record in self.tokens.values()
        )

    async def purge_expired(self, *, now) -> int:
        expired = [key for key, record in self.tokens.items() if record.expires_at < now]
        for key in expired:
            del self.tokens[key]
        return len(expired)


class InMemoryServiceApiKeyRepository:
    def __init__(self) -> None:
        self.key: ServiceApiKeyRecord | None = None

    async def get(self) -> ServiceApiKeyRecord | None:
        return self.key

    async def get_by_key(self, key: str) -> ServiceApiKeyRecord | None:
        if self.key is not None and self.key.key == key:
            return self.key
        return None

    async def replace(self, *, id: str, key: str) -> ServiceApiKeyRecord:
        self.key = ServiceApiKeyRecord(
            id=id,
            key=key,
            last_used_at=None,
            created_at=utc_now(),
        )
        return self.key

    async def touch_last_used(self, key_id: str, *, at) -> None:
        if self.key is not None and self.key.id == key_id:
            self.key.last_used_at = at


__all__ = [
    "InMemoryRefreshTokenRepository",
    "InMemoryServiceApiKeyRepository",
    "InMemoryUserRepository",
]
