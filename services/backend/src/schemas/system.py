"""Schemas describing the running instance."""

from __future__ import annotations

from typing import Literal

from src.schemas.base import APIModel


class SystemInfo(APIModel):
    version: str
    database: Literal["sqlite", "postgresql"]


__all__ = ["SystemInfo"]
