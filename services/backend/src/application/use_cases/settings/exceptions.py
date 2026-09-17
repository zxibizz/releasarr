"""Domain exceptions for the runtime settings use cases."""

from __future__ import annotations


class SettingsError(Exception):
    """Base for settings failures."""


class UnknownSettingKeyError(SettingsError):
    """A PATCH named a field the registry does not expose."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Unknown setting: {key}")
        self.key = key


class SettingLockedError(SettingsError):
    """A PATCH tried to override a field the environment pins."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Setting is set by the environment and cannot be changed here: {key}")
        self.key = key


class InvalidSettingValueError(SettingsError):
    """A PATCH supplied a value the field cannot hold."""

    def __init__(self, key: str, reason: str) -> None:
        super().__init__(f"Invalid value for {key}: {reason}")
        self.key = key
        self.reason = reason


class EmptySettingsUpdateError(SettingsError):
    """A PATCH named no fields at all."""


__all__ = [
    "EmptySettingsUpdateError",
    "InvalidSettingValueError",
    "SettingLockedError",
    "SettingsError",
    "UnknownSettingKeyError",
]
