"""Schemas describing the running instance."""

from __future__ import annotations

from typing import Literal

from src.schemas.base import APIModel


class SystemInfo(APIModel):
    app_name: str
    version: str
    database: Literal["sqlite", "postgresql"]
    url_base: str


__all__ = ["SystemInfo"]
