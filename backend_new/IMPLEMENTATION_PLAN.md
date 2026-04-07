# Backend New Implementation Plan

## Legacy Backend Takeaways
- Legacy service uses layered modules (`application`, `infrastructure`, `api`) wired through a dependency container; that separation keeps routing thin.
- FastAPI app lives in a slim entrypoint that mounts routers and retrieves dependencies from a central registrar.
- Async SQLAlchemy session management and explicit repositories give good transactional boundaries.
- External services (Sonarr, Prowlarr, QBittorrent, TVDB) are wrapped behind interfaces, easing testability and substitution.

## Target Architecture Principles
- Source code for the new backend resides under `src/`, with top-level packages such as `src/api`, `src/application`, `src/domain`, `src/infrastructure`, `src/db`, and `src/settings`.
- Use the OpenAPI contract as the canonical source of truth; data models, enums, and validation all stem from the specification rather than mirroring legacy SQLModel entities.
- Adopt SQLAlchemy 2.0 Declarative models for persistence; expose Pydantic DTOs only to the API layer.
- Centralize dependency wiring (e.g. `src/core/container.py`) so the FastAPI app, CLI tasks, and tests share the same composition root.
- No implicit background schedulers inside the web app: long-running sync/export flows become standalone async tasks or CLI commands we can run separately alongside the API.
- Keep I/O asynchronous end-to-end.
- Standardize tooling around `uv` for dependency management and locking, and `ruff` for linting/formatting.

## Implementation Roadmap
### Phase 0 – Project Foundations *(completed)*
1. Initialize `pyproject.toml` configured for `uv` workflows; add `ruff`, `alembic`, `fastapi`, `pydantic`, `sqlalchemy[asyncio]`, `asyncpg` (or sqlite driver for local), `httpx`.
2. Scaffold package layout under `src/` mirroring the layered architecture (`api`, `application`, `domain`, `infrastructure`, `db`, `core`, `schemas`, `tasks`).
3. Configure `uv` scripts (e.g. `uv run`, `uv pip compile`), set up `ruff.toml`, and add basic CI instructions for lint/test commands.

### Phase 1 – Configuration & Infrastructure *(completed)*
1. Implement `src/settings/config.py` using Pydantic `BaseSettings` (DB URL, API key, pagination defaults, external clients’ base URLs/tokens).
2. Build logging configuration (Loguru or structlog) with contextual logging consistent with the spec’s logging payloads.
3. Create database module: async engine factory, sessionmaker, and `DBManager` abstraction; ensure availability to both API and task runners.
4. Configure Alembic environment to target SQLAlchemy metadata housed in `src/models/__init__.py` (or `src/domain/models.py`).

### Phase 2 – Domain Modeling & Persistence
- [x] Derive SQLAlchemy models directly from OpenAPI schemas (e.g., `MediaRequest`, `Release`, `ReleaseFileMapping`, `RequestLog`, `AsyncJob`).
- [x] Capture spec-defined enumerations (request status, media type, release status) as SQLAlchemy-compatible enums and share them with Pydantic schemas.
- [x] Add timestamp/audit columns demanded by the contract (created/updated timestamps, async job status timestamps).
- [x] Author initial Alembic migration establishing these tables and relationships; keep downgrade scripts healthy.

### Phase 3 – External Integrations & Services
1. Identify integration points required by the new flows (search providers, download clients, metadata services). Reuse transferable logic from the legacy backend but adapt DTOs to the new schema.
2. Define service interfaces (`IReleaseSearcher`, `IDownloadClient`, `ILogSink`, etc.) and concrete implementations under `src/infrastructure` using `httpx.AsyncClient` with timeouts/retries.
3. Create standalone task entrypoints (CLI or module-level async functions) for sync/export jobs so they can run outside the FastAPI process.

### Phase 4 – Application Layer & Use Cases
- [x] Define Pydantic schemas in `src/schemas` mirroring OpenAPI payloads; include pagination envelopes, error responses, async operation descriptors.
- [ ] Implement use cases covering:
   - [x] Request lifecycle (list with filters/pagination, create, retrieve, partial update, delete).
   - [x] Release management (list, create, retrieve, delete, pause/resume, file mapping update, search, download queueing).
   - Logs listing sourced from structured log files (via Loguru) rather than the database.
- [ ] Wire repositories and service adapters into the container so use cases resolve concrete implementations.
- [ ] Implement query/read-model helpers for optimized read patterns (e.g., join-heavy list queries feeding the UI’s DTOs).

### Phase 5 – API Layer
1. Create routers grouped by domain under `src/api/routes` (`requests.py`, `releases.py`, `logs.py`, `jobs.py`).
2. Apply API-key dependency at router or app level; ensure consistent error responses for auth failures.
3. Wire endpoints exactly to OpenAPI specifications (status codes, response models, headers like `Location` for async operations).
4. Implement global exception handlers translating domain/integration errors into the standardized `ErrorResponse`.
5. Provide FastAPI lifespan hooks for resource startup/shutdown (DB connection verification, client session cleanup) but omit background job scheduling.

### Phase 6 – Tasks & Operations
1. Implement standalone async task runners under `src/tasks` (e.g., `sync_missing`, `import_torrent_stats`), reusable by CLI or process manager.
2. Provide CLI entrypoints (Typer or plain `uv run` scripts) so operations can run in parallel with the API server when orchestrated externally.
3. Ensure task runs reuse the same dependency container and logging configuration as the API for consistency.

### Phase 7 – Testing & Validation
1. Set up shared async test fixtures for database (transactional rollbacks) and HTTP clients (`httpx.AsyncClient` against FastAPI app).
2. Write unit tests for repositories, use cases, and services, focusing on spec-derived edge cases (404/409/422, invalid pagination, async job states).
3. Add API contract tests verifying FastAPI-generated OpenAPI matches the provided spec (Schemathesis or openapi-diff).
4. Cover CLI/task entrypoints with smoke tests to ensure they run independently of the web server.

### Phase 8 – Deployment Readiness
1. Integrate Alembic migrations into Docker entrypoint/CI steps; document manual migration commands.
2. Add lightweight health/readiness endpoints (even if not in spec) for infrastructure probes.
3. Prepare seeding/mocking scripts for local development, including fake external services if needed.
4. Document deployment configuration (env vars, ports, run commands) and update CI pipelines for linting (`ruff`), typing (`mypy`), testing, and migration checks.

## Endpoint Coverage Plan
- `/requests` GET/POST → `RequestsRouter` with list/create use cases and pagination helpers derived from spec defaults.
- `/requests/{requestId}` GET/PATCH/DELETE → use cases enforcing status-transition rules and 404/409 semantics.
- `/requests/{requestId}/releases` (deprecated) → optional compatibility route leveraging release query service.
- `/releases` GET/POST → release list/create flows; align `409` conflict checks with spec semantics.
- `/releases/{releaseId}` GET/DELETE → detail + removal use cases with guard rails for async job dependencies.
- `/releases/{releaseId}/pause|resume` POST → async command use cases returning immediate success once the action completes; no async job persistence.
- `/releases/{releaseId}/files/mapping` PUT → mapping updater ensuring atomic replacement and validation of season/episode bindings.
- `/releases/search` GET → external search wrapper; support optional `request_id` correlation.
- `/requests/{requestId}/releases/download` POST → download queueing use case producing async job tracking response.
- `/logs` GET → log query service reading Loguru file output filtered by request id to produce paginated DTOs.

## Cross-Cutting Considerations
- **Authentication**: API key dependency reading `X-API-Key`; configurable secret in settings; responds with `401`/`403` spec-compliant errors.
- **Validation**: Centralize enum/state validation in domain services; partial updates guard immutable fields.
- **Pagination**: Shared helper to normalize `page`/`per_page` with defaults and enforce limits defined in spec.
- **Async Jobs**: Prefer synchronous operations; when async semantics are required return immediate success without persisting job state.
- **Error Handling**: Map domain/integration exceptions to `ErrorResponse`; log with correlation IDs.
- **Observability**: Structured logging with request IDs, metrics hooks for later Prometheus integration; persist Loguru output to file and align log schema with `/logs` response shape.

## Development Rules & Guidelines
### Workflow & Tooling
- Use `uv` for dependency management (`uv add`, `uv lock`, `uv run`). Treat `uv.lock` as source of truth.
- Enforce `ruff` for linting/formatting (`uv run ruff check`/`ruff format`). Combine with `mypy` for typing and `pytest` for tests before commits.
- Maintain feature branches; include OpenAPI references in PR descriptions when endpoints change.

### Code Organization & Style
- Keep all backend code under `src/`; avoid redundant package nesting. Example layout: `src/api`, `src/application`, `src/core`, `src/db`, `src/domain`, `src/infrastructure`, `src/schemas`, `src/tasks`.
- Use dependency injection via constructors/functions; avoid module-level singletons except settings and logging factories.
- Favor concise, purposeful comments only for complex flows.

### Database & Migrations
- Stick to SQLAlchemy Declarative models (`Mapped`, `mapped_column`); share metadata via a central module for Alembic.
- Handle sessions via async context managers (`DBManager.begin_session`) ensuring commit/rollback discipline.
- Every schema change ships with an Alembic migration; include downgrade logic and keep migrations deterministic.

### External Integrations
- Keep credentials in environment variables; never hardcode secrets.
- Wrap HTTP interactions with typed clients, request/response Pydantic DTOs, and retry/backoff policies.
- Provide mock adapters or fixtures for testing integrations without real network calls.

### Testing & Quality
- Organize tests by layer (`tests/unit`, `tests/integration`, `tests/api`, `tests/tasks`).
- Cover negative scenarios (invalid pagination, unauthorized access, state conflicts) matching OpenAPI error codes.
- Validate generated OpenAPI against the canonical `openapi.yaml` as part of CI.

### Operations & Documentation
- Document environment configuration, run commands (`uv run api`, `uv run tasks.sync_missing`) in README/docs.
- Supply Docker instructions wiring the API container and optional task containers.
- Track operational playbooks for running standalone tasks alongside the web server (e.g., systemd services, Kubernetes jobs).
