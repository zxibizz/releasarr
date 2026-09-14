"""Domain exceptions for user management."""

from __future__ import annotations


class UserNotFoundError(Exception):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"User '{user_id}' was not found")


class UsernameTakenError(Exception):
    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Username '{username}' is already taken")


class LastAdminError(Exception):
    def __init__(self) -> None:
        super().__init__("Cannot remove or demote the last active admin")


__all__ = ["LastAdminError", "UserNotFoundError", "UsernameTakenError"]
