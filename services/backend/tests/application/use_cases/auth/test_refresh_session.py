"""Tests for refresh token rotation and reuse detection."""

from __future__ import annotations

import pytest

from src.application.use_cases.auth.exceptions import InvalidRefreshTokenError
from src.application.use_cases.auth.refresh_session import RefreshSessionUseCase
from src.application.use_cases.auth.session_issuer import SessionIssuer
from src.application.use_cases.users.commands import CreateUserCommand
from src.application.use_cases.users.manage_users import CreateUserUseCase
from src.infrastructure.auth.access_tokens import JwtAccessTokenCodec
from src.infrastructure.auth.password_hasher import Argon2PasswordHasher
from tests.application.use_cases.auth.fakes import (
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
)


async def _setup():
    users = InMemoryUserRepository()
    refresh_tokens = InMemoryRefreshTokenRepository()
    issuer = SessionIssuer(
        refresh_tokens=refresh_tokens,
        access_tokens=JwtAccessTokenCodec(secret="test-secret"),
        access_token_ttl_seconds=900,
        session_ttl_seconds=86400,
        remember_ttl_seconds=2_592_000,
    )
    user = await CreateUserUseCase(users=users, password_hasher=Argon2PasswordHasher()).execute(
        CreateUserCommand(username="carol", password="hunter2000")
    )
    use_case = RefreshSessionUseCase(
        users=users, refresh_tokens=refresh_tokens, session_issuer=issuer
    )
    first_session = await issuer.issue(user, remember_me=False)
    return use_case, refresh_tokens, first_session


@pytest.mark.asyncio
async def test_refresh_rotates_the_token_and_keeps_the_family() -> None:
    use_case, refresh_tokens, first_session = await _setup()

    rotated = await use_case.execute(first_session.refresh_token)

    assert rotated.refresh_token != first_session.refresh_token
    assert rotated.access_token
    # The original token is now revoked, not merely superseded.
    from src.application.utility.secret_tokens import hash_token

    original = await refresh_tokens.get_by_hash(hash_token(first_session.refresh_token))
    assert original is not None
    assert original.revoked_at is not None


@pytest.mark.asyncio
async def test_reusing_a_rotated_token_revokes_the_whole_family() -> None:
    use_case, _refresh_tokens, first_session = await _setup()

    rotated = await use_case.execute(first_session.refresh_token)

    # Reusing the already-rotated original must fail...
    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(first_session.refresh_token)

    # ...and burns the token that replaced it too.
    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute(rotated.refresh_token)


@pytest.mark.asyncio
async def test_an_unknown_token_is_rejected() -> None:
    use_case, _, _ = await _setup()

    with pytest.raises(InvalidRefreshTokenError):
        await use_case.execute("not-a-real-token")
