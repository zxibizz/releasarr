"""Reader for the structured (Loguru JSON) log file backing the /logs endpoint."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_LEVEL_MAP = {
    "TRACE": "info",
    "DEBUG": "info",
    "INFO": "info",
    "SUCCESS": "info",
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "error",
}


@dataclass(slots=True)
class LogEntry:
    """A single structured log record exposed to the application layer."""

    id: str
    occurred_at: int
    timestamp: str
    level: str
    message: str
    source: str | None = None
    metadata: dict[str, Any] | None = field(default=None)
    stack_trace: str | None = None


class LogFileReader:
    """Parse Loguru's serialized JSON log file into :class:`LogEntry` records."""

    def __init__(self, log_file: str | Path) -> None:
        self._path = Path(log_file)

    def read_entries(self, request_id: str | None = None) -> list[LogEntry]:
        """Return log entries in chronological order, optionally filtered by request id."""

        if not self._path.exists():
            return []

        entries: list[LogEntry] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                entry = self._parse_line(stripped)
                if entry is None:
                    continue
                if request_id is not None and not self._matches_request(entry, request_id):
                    continue
                entries.append(entry)
        return entries

    @staticmethod
    def _matches_request(entry: LogEntry, request_id: str) -> bool:
        metadata = entry.metadata
        return metadata is not None and metadata.get("request_id") == request_id

    def _parse_line(self, line: str) -> LogEntry | None:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return None

        record = payload.get("record")
        if not isinstance(record, dict):
            return None

        raw_time = record.get("time")
        time_info: dict[str, Any] = raw_time if isinstance(raw_time, dict) else {}
        timestamp_seconds = self._as_float(time_info.get("timestamp"))
        occurred_at = int(timestamp_seconds * 1000)
        timestamp_repr = str(time_info.get("repr", "")) or str(timestamp_seconds)

        raw_level = record.get("level")
        level_info: dict[str, Any] = raw_level if isinstance(raw_level, dict) else {}
        level = _LEVEL_MAP.get(str(level_info.get("name", "INFO")).upper(), "info")

        message = str(record.get("message", ""))
        extra = record.get("extra")
        metadata = dict(extra) if isinstance(extra, dict) else None
        source = record.get("name") or record.get("module")

        stack_trace: str | None = None
        if record.get("exception"):
            stack_trace = str(payload.get("text", "")).strip() or None

        return LogEntry(
            id=self._build_id(line, occurred_at),
            occurred_at=occurred_at,
            timestamp=timestamp_repr,
            level=level,
            message=message,
            source=str(source) if source is not None else None,
            metadata=metadata,
            stack_trace=stack_trace,
        )

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _build_id(line: str, occurred_at: int) -> str:
        digest = hashlib.sha1(line.encode("utf-8")).hexdigest()[:12]
        return f"{occurred_at}-{digest}"


__all__ = ["LogEntry", "LogFileReader"]
