"""Schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import Field

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


__all__ = ["LoginPayload", "LoginResponse", "SetupPayload", "SetupStatus"]
