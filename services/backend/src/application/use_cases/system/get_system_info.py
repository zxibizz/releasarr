"""Use case reporting what this instance is running."""

from __future__ import annotations

from dataclasses import dataclass

APP_NAME = "Releasarr"


@dataclass(slots=True)
class SystemInfo:
    app_name: str
    version: str
    database: str
    url_base: str


@dataclass(slots=True)
class GetSystemInfoUseCase:
    version: str
    database: str
    url_base: str = ""

    async def execute(self) -> SystemInfo:
        return SystemInfo(
            app_name=APP_NAME,
            version=self.version,
            database=self.database,
            url_base=self.url_base,
        )


__all__ = ["GetSystemInfoUseCase", "SystemInfo"]
