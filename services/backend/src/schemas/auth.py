"""Schemas for authentication endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, field_serializer

from src.schemas.base import APIModel
from src.schemas.users import SessionUser


class SetupStatus(APIModel):
    required: bool = Field(description="Whether first-run setup must run before anything else")


class SetupPayload(APIModel):
    username: str
    password: str
    display_name: str | None = None


class LoginPayload(APIModel):
    username: str
    password: str
    remember_me: bool = False


class LoginResponse(APIModel):
    """The refresh token itself never appears here; it only ever travels as a cookie."""

    access_token: str
    user: SessionUser


class ServiceApiKeyInfo(APIModel):
    """Metadata about the single service API key. The plaintext is never included here."""

    prefix: str
    last_used_at: datetime | None = None
    created_at: datetime

    @field_serializer("last_used_at", "created_at")
    def _serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:  # default to UTC when the database returns naive values
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class ServiceApiKeyCreated(APIModel):
    """Returned only from regeneration: the plaintext is never retrievable again."""

    key: ServiceApiKeyInfo
    plaintext: str


__all__ = [
    "LoginPayload",
    "LoginResponse",
    "ServiceApiKeyCreated",
    "ServiceApiKeyInfo",
    "SetupPayload",
    "SetupStatus",
]
