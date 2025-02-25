from __future__ import annotations

import json

import loguru
from pydantic import BaseModel


class DTO_Logs_Record(BaseModel):
    time: str
    level: str
    component: str
    message: str


class DTO_Logs(BaseModel):
    records: list[DTO_Logs_Record]


class Query_ListLogs:
    def __init__(
        self,
        log_file: str,
        logger: loguru.Logger,
    ) -> None:
        self.log_file = log_file
        self.logger = logger

    async def execute(self) -> DTO_Logs:
        self.logger.info("List logs")
        with self.logger.catch(reraise=True):
            return await self._execute()

    async def _execute(self) -> DTO_Logs:
        records = []
        with open(self.log_file, "r") as file:
            lines = file.readlines()[-100:]
            lines.reverse()
            for line in lines:
                log_entry = json.loads(line)
                records.append(
                    DTO_Logs_Record(
                        time=log_entry["record"]["time"]["repr"],
                        level=log_entry["record"]["level"]["name"],
                        component=log_entry["record"]["extra"]["component"],
                        message=log_entry["text"],
                    )
                )
        return DTO_Logs(records=records)
