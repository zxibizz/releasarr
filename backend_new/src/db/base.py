"""Base declarative metadata for SQLAlchemy models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for ORM models."""



metadata = Base.metadata
"""Convenient handle for Alembic auto-generation."""


__all__ = ["Base", "metadata"]
