"""Tests for first-run admin bootstrap."""

from __future__ import annotations

import pytest

from src.application.use_cases.auth.bootstrap_admin import BootstrapAdminUseCase
from src.application.use_cases.auth.commands import BootstrapAdminCommand
from src.application.use_cases.auth.exceptions import SetupAlreadyCompletedError
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.domain.enums import UserRole
from src.infrastructure.auth.access_tokens import JwtAccessTokenCodec
from src.infrastructure.auth.password_hasher import Argon2PasswordHasher
from tests.application.use_cases.auth.fakes import (
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
)


def _make_use_case(users: InMemoryUserRepository) -> BootstrapAdminUseCase:
    issuer = SessionIssuer(
        refresh_tokens=InMemoryRefreshTokenRepository(),
        access_tokens=JwtAccessTokenCodec(secret="test-secret"),
        access_token_ttl_seconds=900,
        session_ttl_seconds=86400,
        remember_ttl_seconds=2_592_000,
    )
    return BootstrapAdminUseCase(
        users=users, password_hasher=Argon2PasswordHasher(), session_issuer=issuer
    )


@pytest.mark.asyncio
async def test_bootstrap_creates_an_active_admin_with_every_permission() -> None:
    users = InMemoryUserRepository()
    use_case = _make_use_case(users)

    session = await use_case.execute(BootstrapAdminCommand(username="root", password="pw123456"))

    assert session.user.role is UserRole.ADMIN
    assert session.user.can_view_all_requests
    assert session.user.can_access_tasks
    assert session.access_token
    assert session.refresh_token


@pytest.mark.asyncio
async def test_bootstrap_refuses_once_a_user_already_exists() -> None:
    users = InMemoryUserRepository()
    use_case = _make_use_case(users)
    await use_case.execute(BootstrapAdminCommand(username="root", password="pw123456"))

    with pytest.raises(SetupAlreadyCompletedError):
        await use_case.execute(BootstrapAdminCommand(username="second", password="pw123456"))
