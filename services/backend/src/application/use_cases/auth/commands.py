"""Input commands for auth use cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LoginCommand:
    username: str
    password: str
    remember_me: bool = False


@dataclass(slots=True)
class BootstrapAdminCommand:
    username: str
    password: str
    display_name: str | None = None


__all__ = ["BootstrapAdminCommand", "LoginCommand"]
