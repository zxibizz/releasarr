"""Authentication and authorization dependencies for the API layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, status

from src.api.errors import api_error
from src.application.use_cases.auth import AuthenticatePrincipalUseCase, Permission, Principal
from src.core.container import get_container


def _authenticate_use_case() -> AuthenticatePrincipalUseCase:
    return get_container().use_cases.auth.authenticate


async def get_principal(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> Principal | None:
    """Resolve the caller from a bearer access token or the service API key.

    Returns ``None`` when no credentials were presented, so a request with no
    auth header at all never touches the database.
    """

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise api_error(
                status.HTTP_401_UNAUTHORIZED,
                "unauthorized",
                "Malformed Authorization header",
            )
        return await _authenticate_use_case().authenticate_bearer(token)

    if x_api_key:
        return await _authenticate_use_case().authenticate_service_key(x_api_key)

    return None


async def require_user(principal: Principal | None = Depends(get_principal)) -> Principal:
    """Require any authenticated caller, session or service."""

    if principal is None:
        raise api_error(status.HTTP_401_UNAUTHORIZED, "unauthorized", "Authentication required")
    return principal


async def require_admin(principal: Principal = Depends(require_user)) -> Principal:
    """Require the caller to be an administrator."""

    if not principal.is_admin:
        raise api_error(
            status.HTTP_403_FORBIDDEN, "forbidden", "Administrator privileges are required"
        )
    return principal


def require_permission(permission: Permission) -> Callable[..., Awaitable[Principal]]:
    """Build a dependency requiring a specific permission flag (or admin)."""

    async def _dependency(principal: Principal = Depends(require_user)) -> Principal:
        if not principal.has(permission):
            raise api_error(
                status.HTTP_403_FORBIDDEN,
                "forbidden",
                f"Missing permission: {permission.value}",
            )
        return principal

    return _dependency


__all__ = ["get_principal", "require_admin", "require_permission", "require_user"]
