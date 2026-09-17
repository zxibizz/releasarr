"""Schemas for the runtime settings endpoints.

The values the API exchanges are plain JSON keyed by field name; the registry in
``src/settings/registry.py`` is what decides which keys exist, which section
they belong to, and how each is typed. Secrets travel in plaintext to admins,
matching the service API key endpoint.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from src.schemas.base import APIModel


class SettingFieldInfo(APIModel):
    """How one editable field behaves, for rendering the form."""

    key: str
    section: str
    kind: str
    is_secret: bool
    requires_restart: bool
    locked: bool = Field(description="True when the environment sets the field explicitly")
    choices: list[str] = Field(default_factory=list)


class SettingsResponse(APIModel):
    """The full settings view: effective values, plus how each field behaves."""

    # section -> {field key: value}, effective values after env overrides apply.
    values: dict[str, dict[str, Any]]
    fields: list[SettingFieldInfo]
    # Flat list of keys the environment pins; PATCH refuses these.
    locked_keys: list[str]
    # Keys whose stored change has not taken effect until a restart.
    pending_restart_keys: list[str]


class UpdateSettingsPayload(APIModel):
    """A partial update to one section: field key -> new value."""

    values: dict[str, Any] = Field(default_factory=dict)


class ConnectionTestPayload(APIModel):
    """Optional candidate credentials, so a value can be tested before saving."""

    url: str | None = None
    api_key: str | None = None
    username: str | None = None
    password: str | None = None


class ConnectionTestResult(APIModel):
    integration: str
    success: bool
    detail: str | None = Field(default=None, description="Failure reason or a short OK summary")


__all__ = [
    "ConnectionTestPayload",
    "ConnectionTestResult",
    "SettingFieldInfo",
    "SettingsResponse",
    "UpdateSettingsPayload",
]
