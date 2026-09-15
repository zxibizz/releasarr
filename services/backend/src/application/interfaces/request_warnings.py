"""Ports for persisting and reading request-scoped warnings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from src.domain.enums import RequestWarningCode


@dataclass(slots=True)
class RequestWarningRecord:
    """One warning row: a (request, release, code) triple.

    ``release_id`` is nullable so a future request-only code (nothing to blame
    on a specific release) has somewhere to leave it unset. ``created_at`` is
    ignored on write - the repository stamps it - and only meaningful on read.
    """

    request_id: str
    code: RequestWarningCode
    release_id: str | None = None
    details: dict[str, object] | None = None
    created_at: datetime | None = None


class RequestWarningRepository(Protocol):
    """Persistence for `request_warnings`.

    Two write primitives because the two codes this ships with clear on
    different scopes: mapping overlap is recomputed over a request's whole
    release set, so a resolved overlap must be cleared request-wide; a regrab
    failure is per-release, so clearing it must not touch a sibling release's
    own fresh failure. See `RequestWarningSynchronizer` and
    `RegrabOutdatedReleasesUseCase` for the callers of each.
    """

    async def replace_for_requests(
        self,
        code: RequestWarningCode,
        request_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        """Replace every `code` row for `request_ids` with `warnings`.

        An empty `warnings` sequence is how a caller clears its own code for
        those requests - this is a full replace, not a merge.
        """

    async def replace_for_releases(
        self,
        code: RequestWarningCode,
        release_ids: Sequence[str],
        warnings: Sequence[RequestWarningRecord],
    ) -> None:
        """Replace every `code` row for `release_ids` with `warnings`."""

    async def delete_for_release(self, release_id: str) -> None:
        """Remove every warning naming this release, for any request.

        Used when a release is deleted outright. Not implied by the FK
        `ondelete` - see the repository implementation for why.
        """

    async def delete_for_request_release(self, request_id: str, release_id: str) -> None:
        """Remove warnings naming this exact (request, release) pair.

        Used when a release is unlinked from one request but kept for others:
        no FK is violated by an unlink, so nothing cascades on its own.
        """

    async def list_for_requests(
        self, request_ids: Sequence[str]
    ) -> dict[str, list[RequestWarningRecord]]:
        """Every warning for each of `request_ids`, keyed by request id."""

    async def list_for_releases(
        self, release_ids: Sequence[str]
    ) -> dict[str, list[RequestWarningRecord]]:
        """Every warning naming each of `release_ids`, keyed by release id."""


__all__ = ["RequestWarningRecord", "RequestWarningRepository"]
