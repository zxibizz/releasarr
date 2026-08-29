"""Shared pydantic configuration helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base class for all response/request models."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, use_enum_values=True)


__all__ = ["APIModel"]
