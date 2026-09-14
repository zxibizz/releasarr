"""Domain exceptions for authentication and session management."""

from __future__ import annotations


class InvalidCredentialsError(Exception):
    """Raised when a username/password pair does not match."""

    def __init__(self) -> None:
        super().__init__("Invalid username or password")


class AccountLockedError(Exception):
    """Raised when a user has too many recent failed logins."""

    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Account is temporarily locked due to repeated failed logins")


class InactiveUserError(Exception):
    """Raised when a deactivated user attempts to authenticate."""

    def __init__(self) -> None:
        super().__init__("This account has been deactivated")


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token is missing, expired, or already used."""

    def __init__(self) -> None:
        super().__init__("Refresh token is invalid or expired")


class InvalidAccessTokenError(Exception):
    """Raised when an access token fails signature or expiry validation."""

    def __init__(self) -> None:
        super().__init__("Access token is invalid or expired")


class PermissionDeniedError(Exception):
    """Raised when a principal lacks a required permission."""

    def __init__(self, permission: str) -> None:
        self.permission = permission
        super().__init__(f"Missing permission: {permission}")


class SetupAlreadyCompletedError(Exception):
    """Raised when bootstrap is attempted after the first user already exists."""

    def __init__(self) -> None:
        super().__init__("Setup has already been completed")


__all__ = [
    "AccountLockedError",
    "InactiveUserError",
    "InvalidAccessTokenError",
    "InvalidCredentialsError",
    "InvalidRefreshTokenError",
    "PermissionDeniedError",
    "SetupAlreadyCompletedError",
]
