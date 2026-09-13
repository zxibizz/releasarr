# Backend guide

Concrete patterns for `services/backend/`. Paths are relative to `services/backend/`. Read
[`architecture.md`](architecture.md) first for the layering rationale.

## Adding an API endpoint

The full checklist, in dependency order. Skip the steps that do not apply.

1. **Schema change?** Edit `src/domain/models.py`, then create a migration (see below).
2. **New port?** Add a `Protocol` plus its record dataclasses to
   `src/application/interfaces/<area>.py`.
3. **New adapter?** Implement it in `src/infrastructure/<area>/`.
4. **Use case** in `src/application/use_cases/<area>/<verb>.py`, exported from that package's
   `__init__.py`.
5. **Register it** as a `@cached_property` in the right group in `src/core/container.py`.
6. **Pydantic schemas** in `src/schemas/<area>.py`, extending `APIModel`.
7. **Route** in `src/api/routes/<area>.py`, and `include_router` in
   `src/api/routes/__init__.py` if the router is new.
8. **Domain exceptions** into `DOMAIN_ERROR_MAP` in `src/api/errors.py`.
9. **Update `../../openapi.yaml`** and confirm `uv run pytest tests/api/test_openapi_contract.py`.

### Routers

One file per domain in `src/api/routes/`. Auth is applied at router level, so every route in it
requires `X-API-Key`:

```python
router = APIRouter(prefix="/requests", tags=["Requests"], dependencies=[Depends(require_api_key)])
```

Collection handlers use `""` as their path, not `"/"`. Tags must match the tag names in
`openapi.yaml`. Path params that are camelCase in the spec get an alias:

```python
RequestIdParam = Annotated[str, Path(..., alias="requestId")]
```

### Injecting use cases

Every route file repeats this trio. Use cases are pulled from the container, never constructed
in the handler:

```python
def _get_container() -> AppContainer:
    return get_container()


def _get_list_use_case(
    container: AppContainer = Depends(_get_container),
) -> ListMediaRequestsUseCase:
    return container.use_cases.media_requests.list
```

These `_get_*` functions are also the seam the API tests override — see
[`testing.md`](testing.md).

### Handlers

Thin by design: parse, map to a command, await, map the DTO back.

```python
@router.post(
    "/requests",
    response_model=AddRequestResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ADD_REQUEST_RESPONSES,
)
async def add_request(
    payload: AddRequestPayload,
    add_request_use_case: AddMediaRequestUseCase = Depends(_add_request_use_case),
) -> AddRequestResponse:
    command = AddMediaRequestCommand(
        media_type=MediaType(payload.type),
        provider_id=payload.provider_id,
        root_folder_path=payload.root_folder_path,
        season_numbers=list(payload.season_numbers or []),
        monitor_new_seasons=payload.monitor_new_seasons,
    )
    requests = await add_request_use_case.execute(command)
    return AddRequestResponse(requests=[_dto_to_schema(dto) for dto in requests])
```

`responses=` is built with `error_responses({404: "…", 502: "…"})` from `src/api/responses.py`
and only documents the error shape; it does not enforce anything. `DELETE` handlers return
`Response(status_code=status.HTTP_204_NO_CONTENT)`.

### Errors

Domain exceptions are raised by use cases and mapped centrally. Do not `try/except` them in a
route:

```python
DOMAIN_ERROR_MAP: dict[type[Exception], tuple[int, str]] = {
    MediaRequestNotFoundError: (status.HTTP_404_NOT_FOUND, "request_not_found"),
    EmptyUpdatePayloadError: (status.HTTP_400_BAD_REQUEST, "empty_update"),
    HttpClientError: (status.HTTP_502_BAD_GATEWAY, "upstream_error"),
}
```

The handler emits `{"code", "message", "details"}`, with `message` taken from `str(exc)`.
Unmapped exceptions become a 500 with `internal_error` and a logged traceback.

Route-layer validation — an unparseable query enum, say — raises `api_error(...)` directly:

```python
raise api_error(status.HTTP_400_BAD_REQUEST, "invalid_status_filter", str(exc)) from exc
```

Exceptions live in `src/application/use_cases/<area>/exceptions.py`, subclass the closest stdlib
type (`LookupError` for not-found, `ValueError` for bad input, `RuntimeError` for
upstream/config), carry a human-readable message, and store structured attributes for tests:

```python
class MediaRequestNotFoundError(LookupError):
    def __init__(self, request_id: str):
        super().__init__(f"Media request '{request_id}' was not found")
        self.request_id = request_id
```

### Schemas

All API models extend `APIModel` (`src/schemas/base.py`), which sets `from_attributes=True`
(so `Model.model_validate(dto)` works on dataclasses), `populate_by_name=True`, and
`use_enum_values=True`.

Naming: `MovieRequest` / `SeriesRequest` for entities, `CreateMovieRequest` for payloads,
`MediaRequestUpdate` for patches (all fields optional), `RequestsResponse` extending
`PaginatedResponse` for pages. Movie/series pairs are joined by a discriminated union:

```python
MediaRequest = Annotated[MovieRequest | SeriesRequest, Field(discriminator="type")]
```

## Use cases

One class per operation, named `{Verb}{Entity}UseCase`. Dependencies are protocol-typed and
injected via `__init__` — keyword-only once there are several:

```python
class AddMediaRequestUseCase:
    def __init__(
        self,
        *,
        repository: MediaRequestRepository,
        sonarr_service: SonarrService,
        radarr_service: RadarrService,
        logger: Logger | None = None,
    ) -> None:
        self._repository = repository
        self._sonarr = sonarr_service
        self._radarr = radarr_service
        self._logger = logger or get_logger(component="add_media_request")
```

The entry point is always `async def execute(...)`. Its shape varies with the operation: no
args, a command object, an id, an id plus a command, or an options object. Use cases raise
domain exceptions and never touch HTTP types.

Use cases may depend on other use cases — `DiscoverUseCases.add_request` takes `sync_sonarr`
from the media-requests group so adding to Sonarr immediately reconciles requests.

### commands / dto / mappers

| File | Contains | Direction |
| --- | --- | --- |
| `commands.py` | Input dataclasses built by the route | API → use case |
| `dto.py` | Output dataclasses returned to the route | use case → API |
| `mappers.py` | Pure `record_to_dto`-style functions | repository record → DTO |
| `exceptions.py` | Domain errors for the area | — |

All are `@dataclass(slots=True)`. Commands that only one use case needs may live in that use
case's own module instead (see `discover/add_request.py`).

Partial updates use the `UNSET` sentinel, because `None` is a meaningful value — "clear this
field" — and must stay distinguishable from "not provided":

```python
@dataclass(slots=True)
class UpdateMediaRequestCommand:
    title: str | None | _Unset = field(default=UNSET)

    def is_empty(self) -> bool:
        return all(value is UNSET for value in self.__dict__.values())
```

The same sentinel appears at the repository boundary in `UpdateMediaRequestData`.

### Logging

Bind a component once, then log with structured kwargs. Never interpolate identifiers into the
message — the log reader parses them out of Loguru's `extra` to power `/logs?request_id=`:

```python
self._logger.info(
    "Added series requests",
    tvdb_id=command.provider_id,
    sonarr_series_id=series_id,
    seasons=seasons,
    requests=len(request_ids),
)
```

Conventional fields: `component`, `request_id`, `task`, `job_id`, `trigger`. Task binding is
handled for you — `SyncSteps.for_kind` wraps each step in `logger.contextualize(task=kind)`, so
anything logged several layers down is filterable by task.

`configure_logging` installs a `redact_secrets` patcher that masks query-param secrets, and
mutes `httpx`/`httpcore` to WARNING, so API keys do not reach the log file. Keep it that way.

## Interfaces and adapters

Ports are `typing.Protocol`, not ABCs. The record dataclasses a protocol passes around live in
the same module:

```python
@dataclass(slots=True)
class MediaRequestRecord:
    id: str
    media_type: MediaType
    status: MediaRequestStatus
    localizations: dict[str, MediaLocalization] = field(default_factory=dict)


class MediaRequestRepository(Protocol):
    async def list_requests(
        self, *, page: int, per_page: int,
        status: MediaRequestStatus | None, media_type: MediaType | None,
    ) -> tuple[list[MediaRequestRecord], int]: ...
```

Implementations satisfy the protocol structurally, though repositories usually declare it
explicitly for clarity.

### HTTP clients

`src/infrastructure/http/BaseHttpClient` wraps `httpx.AsyncClient` and owns the shared
behaviour: a 15s default timeout, two retries on transport errors and on `429/500/502/503/504`,
and `HttpClientError` on give-up (mapped to 502 at the API). An *arr client injects its key as a
header and exposes `aclose()`:

```python
class SonarrHttpClient(SonarrService):
    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float = 15.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._http = BaseHttpClient(
            base_url=base_url, headers={"X-Api-Key": api_key},
            timeout=timeout_seconds, transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()
```

The `transport` parameter exists so tests can inject `httpx.MockTransport`. Keep it.

Base URLs are passed through verbatim, so they must already include the provider's API path:
Sonarr/Radarr `…/api/v3`, Prowlarr `…/api/v1`, qBittorrent `…/api/v2`.

### Repositories

`BaseSqlAlchemyRepository` (`src/db/repository.py`) holds a `DBManager` and provides `_count`
and `_paginate`. Reads use `self.db.session()`, writes use `self.db.transaction()` (which
commits on exit):

```python
async with self.db.transaction() as session:
    ...
```

A private `_to_record()` maps the ORM model to the interface dataclass. Use cases must never see
a SQLAlchemy model.

## The container

`src/core/container.py` is the composition root: nested dataclass groups, one `@cached_property`
per dependency.

```
AppContainer
├── settings, db_manager
├── repositories    → media_requests, releases, sync_jobs, scheduled_tasks
├── services        → sonarr, radarr, tvdb, tmdb, qbittorrent_client,
│                     release_search, release_download, release_lifecycle
├── queries
├── use_cases       → discover, logs, media_requests, releases, tasks
└── infrastructure  → log_reader
```

`get_container()` is `@lru_cache`d. `startup()` configures logging; `shutdown()` calls `aclose()`
on any service that has it and flushes Loguru.

Optional integrations degrade here rather than at the call site:

```python
@cached_property
def release_search(self) -> ReleaseSearchService:
    settings = self._container.settings
    if settings.prowlarr_url and settings.prowlarr_api_key.get_secret_value():
        return ProwlarrReleaseSearchService(...)
    return InMemoryReleaseSearchService()
```

qBittorrent returns `None` when unconfigured, and the download/lifecycle services fall back to
in-memory stubs. TVDB and TMDB return `None`, and the use cases accept `TvdbService | None`.
Sonarr and Radarr are always constructed and fail at request time if the key is missing.

To add a dependency: implement it, export it from its package `__init__.py`, add a
`@cached_property` to the appropriate group, and wire its own dependencies inside that property.

## Settings

Add a typed field to `AppSettings` in `src/settings/config.py`. The env var is the field name
upper-cased with the `RELEASARR_` prefix. Use `SecretStr` for anything credential-shaped.

```python
prowlarr_timeout: float = Field(default=20.0)   # RELEASARR_PROWLARR_TIMEOUT
```

Read them from `container.settings` when wiring, or take `settings: AppSettings | None = None`
in a use case and default to `get_settings()`. Document new variables in the `README.md` tables.

## Migrations

Run from `services/backend/`:

```bash
uv run alembic revision --autogenerate -m "add thing"
uv run alembic upgrade head
uv run alembic downgrade -1
```

`alembic/env.py` reads `get_settings().database_url` and imports `src.domain.models` so the
metadata is populated. Autogenerate runs with `compare_type=True` and
`compare_server_default=True`.

**Always review the generated file.** Enums are the trap: on SQLite they are VARCHAR with a
CHECK constraint and `batch_alter_table` recreates the table cleanly, but on PostgreSQL they are
native types where that same operation casts to the *existing* type and silently changes
nothing. Migration `d3e9a17c5b42_repair_sync_job_kind_enum.py` exists solely to undo that
mistake. When changing an enum's labels, branch on the dialect and write the Postgres path by
hand: column to `text`, delete or rewrite invalid rows, drop and recreate the type, cast back.

## Tasks and the CLI

Recurring work is defined once, in `src/application/use_cases/tasks/definitions.py`, and shared
by the scheduler and the API so the UI cannot disagree with what runs. `src/tasks/sync_steps.py`
holds the step implementations; `src/tasks/cli.py` is a Typer app for one-shot runs.

Adding a task means: a new `SyncJobKind` member (with a migration for the enum), a definition
with its interval, a step in `SyncSteps`, and a CLI command if it is useful standalone. Read
[`../services/backend/docs/tasks.md`](../services/backend/docs/tasks.md) — it covers job collapsing, ordering
guarantees, and log binding in detail.
