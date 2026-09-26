"""Use case reporting what this instance is running."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SystemInfo:
    version: str
    database: str


@dataclass(slots=True)
class GetSystemInfoUseCase:
    version: str
    database: str

    async def execute(self) -> SystemInfo:
        return SystemInfo(version=self.version, database=self.database)


__all__ = ["GetSystemInfoUseCase", "SystemInfo"]
