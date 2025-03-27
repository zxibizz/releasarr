from __future__ import annotations

import json

import loguru
from pydantic import BaseModel


class ListLogsResponse__Record(BaseModel):
    time: str
    level: str
    component: str
    message: str


class ListLogsResponse(BaseModel):
    records: list[ListLogsResponse__Record]


class Query_ListLogs:
    def __init__(
        self,
        log_file: str,
        logger: loguru.Logger,
    ) -> None:
        self.log_file = log_file
        self.logger = logger

    async def execute(self) -> ListLogsResponse:
        self.logger.info("List logs")
        with self.logger.catch(reraise=True):
            return await self._execute()

    async def _execute(self) -> ListLogsResponse:
        records = []
        with open(self.log_file, "r") as file:
            lines = file.readlines()[-100:]
            lines.reverse()
            for line in lines:
                log_entry = json.loads(line)
                records.append(
                    ListLogsResponse__Record(
                        time=log_entry["record"]["time"]["repr"],
                        level=log_entry["record"]["level"]["name"],
                        component=log_entry["record"]["extra"]["component"],
                        message=log_entry["text"],
                    )
                )
        return ListLogsResponse(records=records)
