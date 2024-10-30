from typing import Protocol

from src.application.schemas import ReleaseData


class I_ReleaseSearcher(Protocol):
    async def search(self, search_string) -> list[ReleaseData]: ...
