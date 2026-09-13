"""Reader for the structured (Loguru JSON) log file backing the /logs endpoint."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.domain.enums import LogService

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

    def __init__(self, log_file: str | Path, history_files: int = 1) -> None:
        self._path = Path(log_file)
        # Reading every surviving rotation would make each call scale with the
        # retention window, so only the most recent few are in reach.
        self._history_files = max(1, history_files)

    def read_entries(
        self,
        request_id: str | None = None,
        task: str | None = None,
        service: str | None = None,
    ) -> list[LogEntry]:
        """Return log entries in chronological order, optionally filtered.

        Filters are combined, and all three match on fields the producer bound
        onto the record rather than on the message text.
        """

        entries: list[LogEntry] = []
        for path in self._log_files():
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    entry = self._parse_line(stripped)
                    if entry is None:
                        continue
                    if request_id is not None and not self._matches(
                        entry, "request_id", request_id
                    ):
                        continue
                    if task is not None and not self._matches(entry, "task", task):
                        continue
                    if service is not None and self._service_of(entry) != service.lower():
                        continue
                    entries.append(entry)
        return entries

    @staticmethod
    def _service_of(entry: LogEntry) -> str:
        """Return the process that wrote a record, as ``LogService`` spells it.

        The processes tag every record they write, but ones written before they
        did would otherwise match neither service and vanish from the view. Work
        done inside a background task always has ``task`` bound onto it by
        ``SyncSteps.for_kind``, so that field is what separates the worker's
        records from request handling.
        """

        metadata = entry.metadata
        if metadata is not None:
            raw = metadata.get("service")
            if raw is not None:
                return str(raw).lower()
            if "task" in metadata:
                return LogService.SCHEDULER.value
        return LogService.API.value

    def _log_files(self) -> list[Path]:
        """Return the files to scan, oldest first.

        Rotation moves history out of the configured path into a timestamped
        sibling (``backend.log`` becomes ``backend.2026-09-13_04-54-26_300466.log``),
        so reading only the active file would drop everything logged before the
        last rotation.
        """
        rotated = [
            path
            for path in self._path.parent.glob(f"{self._path.stem}.*{self._path.suffix}")
            if path != self._path and path.is_file()
        ]
        rotated.sort(key=lambda path: (path.stat().st_mtime, path.name))

        # The active file counts against the budget and is always the newest.
        keep = self._history_files - 1
        recent = rotated[-keep:] if keep > 0 else []
        return [path for path in [*recent, self._path] if path.exists()]

    @staticmethod
    def _matches(entry: LogEntry, key: str, value: str) -> bool:
        metadata = entry.metadata
        return metadata is not None and metadata.get(key) == value

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
