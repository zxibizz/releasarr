"""Inert filler collaborators for use cases whose tests don't exercise them.

`tests/fakes.py` holds *stateful* fakes a test asserts against. These are
`create_autospec` doubles for a use case's *other* required collaborators - the
ones a given test doesn't care about - pre-armed with the same safe fallback
behaviour their old `is None` guards used to provide, so a test exercising one
collaborator doesn't have to hand-write fakes for the rest.
"""

from __future__ import annotations

from unittest.mock import create_autospec

from src.application.interfaces.media_requests import MediaRequestRepository
from src.application.interfaces.radarr import RadarrService
from src.application.interfaces.releases import ReleaseRepository
from src.application.interfaces.request_warnings import RequestWarningRepository
from src.application.use_cases.releases.auto_mapping import ReleaseAutoMapper
from src.application.use_cases.releases.replace_existing import ExistingReleaseReplacer
from src.application.use_cases.releases.warnings import RequestWarningSynchronizer
from src.application.use_cases.requests.recompute_state import RecomputeRequestStateUseCase
from src.application.use_cases.requests.state import RequestStateDeriver
from src.application.use_cases.tasks.enqueue_sync import EnqueueSyncJobUseCase


def stub_media_request_repository() -> MediaRequestRepository:
    """A `MediaRequestRepository` double that finds and changes nothing."""

    repository = create_autospec(MediaRequestRepository, instance=True)
    repository.get_request.return_value = None
    # `ReleaseAutoMapper`'s sibling lookups must come back empty, or a bare
    # autospec mock would offer a bogus record built from another Mock.
    repository.find_by_sonarr.return_value = None
    repository.list_radarr_requests.return_value = []
    return repository


def stub_release_repository() -> ReleaseRepository:
    """A `ReleaseRepository` double reporting no linked releases."""

    repository = create_autospec(ReleaseRepository, instance=True)
    repository.get_releases_for_requests.return_value = []
    repository.list_request_ids_with_releases.return_value = []
    return repository


def stub_warning_repository() -> RequestWarningRepository:
    """A `RequestWarningRepository` double reporting no warnings."""

    repository = create_autospec(RequestWarningRepository, instance=True)
    repository.list_for_requests.return_value = {}
    repository.list_for_releases.return_value = {}
    return repository


def stub_warning_synchronizer() -> RequestWarningSynchronizer:
    """A `RequestWarningSynchronizer` double that never writes anything."""

    return create_autospec(RequestWarningSynchronizer, instance=True)


def stub_recompute_state() -> RecomputeRequestStateUseCase:
    """A `RecomputeRequestStateUseCase` double that never writes anything."""

    return create_autospec(RecomputeRequestStateUseCase, instance=True)


def stub_auto_mapper() -> ReleaseAutoMapper:
    """A `ReleaseAutoMapper` double that maps nothing and offers no candidates."""

    mapper = create_autospec(ReleaseAutoMapper, instance=True)
    mapper.apply.return_value = []
    mapper.candidate_requests.return_value = []
    mapper.suggest.return_value = ([], [])
    return mapper


def stub_existing_release_replacer() -> ExistingReleaseReplacer:
    """An `ExistingReleaseReplacer` double reporting no releases to replace.

    The empty list is load-bearing: a truthy result here would make a grab
    wrongly demand an `existing_releases` decision from the caller.
    """

    replacer = create_autospec(ExistingReleaseReplacer, instance=True)
    replacer.existing_for.return_value = []
    return replacer


def stub_enqueue_sync() -> EnqueueSyncJobUseCase:
    """An `EnqueueSyncJobUseCase` double that queues nothing."""

    return create_autospec(EnqueueSyncJobUseCase, instance=True)


def real_deriver() -> RequestStateDeriver:
    """`RequestStateDeriver` is a pure, stateless algorithm - use the real thing."""

    return RequestStateDeriver()


def stub_radarr() -> RadarrService:
    """A `RadarrService` double for a test that never touches the movie path."""

    return create_autospec(RadarrService, instance=True)


__all__ = [
    "real_deriver",
    "stub_auto_mapper",
    "stub_enqueue_sync",
    "stub_existing_release_replacer",
    "stub_media_request_repository",
    "stub_radarr",
    "stub_recompute_state",
    "stub_release_repository",
    "stub_warning_repository",
    "stub_warning_synchronizer",
]
