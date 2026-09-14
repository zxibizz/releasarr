"""Tests for the login use case: success, failure, and lockout."""

from __future__ import annotations

import pytest

from src.application.use_cases.auth.commands import LoginCommand
from src.application.use_cases.auth.exceptions import (
    AccountLockedError,
    InvalidCredentialsError,
)
from src.application.use_cases.auth.login import LoginUseCase
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.application.utility.secret_tokens import hash_token
from src.infrastructure.auth.access_tokens import JwtAccessTokenCodec
from src.infrastructure.auth.password_hasher import Argon2PasswordHasher
from tests.application.use_cases.auth.fakes import (
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
)


def _make_login_use_case(*, max_failed_logins: int = 3, lockout_seconds: int = 900):
    users = InMemoryUserRepository()
    refresh_tokens = InMemoryRefreshTokenRepository()
    hasher = Argon2PasswordHasher()
    issuer = SessionIssuer(
        refresh_tokens=refresh_tokens,
        access_tokens=JwtAccessTokenCodec(secret="test-secret"),
        access_token_ttl_seconds=900,
        session_ttl_seconds=86400,
        remember_ttl_seconds=2_592_000,
    )
    use_case = LoginUseCase(
        users=users,
        password_hasher=hasher,
        session_issuer=issuer,
        max_failed_logins=max_failed_logins,
        lockout_seconds=lockout_seconds,
    )
    return use_case, users, refresh_tokens, hasher


@pytest.mark.asyncio
async def test_login_succeeds_and_issues_a_session() -> None:
    use_case, users, refresh_tokens, hasher = _make_login_use_case()
    from src.application.use_cases.users.commands import CreateUserCommand
    from src.application.use_cases.users.manage_users import CreateUserUseCase

    creator = CreateUserUseCase(users=users, password_hasher=hasher)
    await creator.execute(CreateUserCommand(username="Alice", password="correct horse"))

    session = await use_case.execute(LoginCommand(username="alice", password="correct horse"))

    assert session.access_token
    assert session.refresh_token
    assert session.user.username == "alice"
    stored = await refresh_tokens.get_by_hash(hash_token(session.refresh_token))
    assert stored is not None
    assert stored.remember is False


@pytest.mark.asyncio
async def test_login_rejects_an_unknown_username() -> None:
    use_case, *_ = _make_login_use_case()

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(LoginCommand(username="ghost", password="whatever"))


@pytest.mark.asyncio
async def test_login_locks_the_account_after_too_many_failures() -> None:
    use_case, users, _, hasher = _make_login_use_case(max_failed_logins=2)
    from src.application.use_cases.users.commands import CreateUserCommand
    from src.application.use_cases.users.manage_users import CreateUserUseCase

    await CreateUserUseCase(users=users, password_hasher=hasher).execute(
        CreateUserCommand(username="bob", password="the-real-password")
    )

    for _ in range(2):
        with pytest.raises(InvalidCredentialsError):
            await use_case.execute(LoginCommand(username="bob", password="wrong"))

    with pytest.raises(AccountLockedError):
        await use_case.execute(LoginCommand(username="bob", password="the-real-password"))
