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

One file per domain in `src/api/routes/`. Auth is applied at router level (or per-route, where
one router mixes public and gated endpoints — see `routes/users.py`):

```python
router = APIRouter(prefix="/requests", tags=["Requests"], dependencies=[Depends(require_user)])
```

`require_user` accepts either a bearer access token or a service API key (see "Auth and
permissions" below); routes that need more than "authenticated" use `require_admin` or
`require_permission(Permission.X)` instead. Collection handlers use `""` as their path, not
`"/"`. Tags must match the tag names in `openapi.yaml`. Path params that are camelCase in the
spec get an alias:

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

### Auth and permissions

`src/api/dependencies/auth.py` resolves a `Principal` (`src/application/use_cases/auth/permissions.py`)
from either an `Authorization: Bearer` access token (a session, from `/auth/login`) or an
`X-API-Key` header (the service key, which always authenticates as a full admin — it isn't bound
to any user account). Three dependencies build on it:

```python
require_user                              # any authenticated principal
require_admin                             # principal.user.role == UserRole.ADMIN
require_permission(Permission.TASKS)      # admin, or the matching per-user flag
```

`Permission` is a flat enum (`view_all_requests`, `tasks`, `indexers`, `logs`, `manage_users`);
`has_permission()` gives admins every permission unconditionally. A route needing more than one
check (e.g. an admin-only field on an otherwise self-service endpoint) takes `principal:
Principal = Depends(require_user)` and checks `principal.is_admin` / `principal.has(...)` itself
— see `owner_user_id` handling in `update_request` in `routes/requests.py`.

Ownership follows the same principal: `RequestScope.for_user(principal.user)` is `unrestricted()`
for an admin or anyone with `view_all_requests`, otherwise `owned_by(user.id)`. Pass
`scope.owner_user_id` into `ListRequestsOptions`, and for a single-resource route, only pay for
the extra fetch needed to check ownership when `principal.scope.is_restricted` — an unrestricted
caller (the common case) makes one repository call, not two. An out-of-scope request raises the
same `MediaRequestNotFoundError` as a truly missing one: a 403 would confirm the row exists.

Root-folder restriction works the same way: `allowed_root_folders(principal.user)` returns
`None` for an unrestricted caller (including an empty allow-list, which means "no restriction",
not "nothing allowed") or the user's list otherwise, passed to `ListRootFoldersUseCase.execute`
and `AddMediaRequestCommand.allowed_root_folders`.

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
        self._logger = logger or get_logger(LogComponent.USECASE_ADD_REQUEST)
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
        return all(getattr(self, f.name) is UNSET for f in fields(self))
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
├── repositories    → media_requests, releases, sync_jobs, scheduled_tasks,
│                     users, refresh_tokens, service_api_keys
├── services        → sonarr, radarr, tvdb, tmdb, qbittorrent_client,
│                     release_search, release_download, release_lifecycle,
│                     password_hasher, access_token_codec
├── queries
├── use_cases       → auth, discover, logs, media_requests, releases, tasks, users
└── infrastructure  → log_reader
```

`get_container()` is `@lru_cache`d. `startup()` configures logging and refuses to boot if
`auth_secret` is empty (a blank signing secret would mean any deployment's tokens are forgeable
from the public source); `shutdown()` calls `aclose()` on any service that has it and flushes
Loguru.

Optional integrations degrade here rather than at the call site:

```python
@cached_property
def release_search(self) -> ReleaseSearchService:
    return ProwlarrReleaseSearchService(base_url=settings.prowlarr_url, ...)
```

Every provider is built either way, configured or not: nothing is `None`, and nothing stands in
for a missing one. Their ports declare `is_configured`, the adapter answers it from the settings
it was given, and a caller that cannot work without one reports that rather than receiving a stub
that cannot do the job. A public endpoint turns that into a 503; a background step skips. Sonarr
and Radarr are always constructed and fail at request time if the key is missing.

To add a dependency: implement it, export it from its package `__init__.py`, add a
`@cached_property` to the appropriate group, and wire its own dependencies inside that property.

## Settings

Settings come in two layers. The base is `AppSettings` in `src/settings/config.py`, read from
environment variables (field name upper-cased, `RELEASARR_` prefix) once per process and cached by
`get_settings()`. On top of it sits an override layer persisted in the `app_settings` table and
edited through the `/settings` API.

The registry in `src/settings/registry.py` is the single declaration of which fields are editable:
each entry names its `AppSettings` field, the section it belongs to, its value shape, whether it is
a secret, and whether a change needs a restart. Adding an editable setting is a new `SettingField`
row there plus the `AppSettings` field; the read response, PATCH validation, and the UI form all
derive from that one declaration.

```python
SettingField("prowlarr_timeout", "network", "float"),
```

Resolution and hot-reload are the provider's job. `LayeredSettingsProvider`
(`src/infrastructure/settings/provider.py`) composes the env base with the stored overrides, and
`AppContainer.settings` resolves through it. A field the environment sets explicitly is locked:
its key is in the env instance's `model_fields_set`, a stored override for it is ignored, and the
API rejects a PATCH of it. Every edit bumps a `revision` on the row; both processes poll it
(`AppContainer.apply_settings_updates()`, called from the request middleware and each scheduler
loop) and, on a change, drop their cached service and use-case containers so the next resolve
rebuilds clients from the new settings. A field marked `requires_restart` is read once at process
startup (logging, auth wiring) and is not re-applied live.

For an env-only setting that is never editable, add the `AppSettings` field and read it as before,
but leave it out of the registry — and list it in `READONLY_KEYS` so the UI shows it as fixed.

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

## Tasks

Recurring work is defined once, in `src/application/use_cases/tasks/definitions.py`, and shared
by the scheduler and the API so the UI cannot disagree with what runs. `src/tasks/sync_steps.py`
holds the step implementations; a one-shot run is `POST /tasks/run/{kind}`, not a CLI.

Adding a task means: a new `SyncJobKind` member (with a migration for the enum), a definition
with its interval, and a step in `SyncSteps`. Read
[`../services/backend/docs/tasks.md`](../services/backend/docs/tasks.md) — it covers job collapsing, ordering
guarantees, and log binding in detail.
