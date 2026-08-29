"""Shared sentinel for distinguishing omitted fields from explicit null values.

Implemented as a single-member :class:`enum.Enum` so static type checkers can
narrow ``X | _Unset`` unions on ``is``/``is not UNSET`` comparisons.
"""

from __future__ import annotations

import enum
from typing import Final


class _Unset(enum.Enum):
    """Sentinel type used to mark fields that were not supplied."""

    UNSET = enum.auto()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "UNSET"


UNSET: Final = _Unset.UNSET
"""Singleton sentinel value."""


__all__ = ["UNSET", "_Unset"]
