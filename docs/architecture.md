# Architecture

How the pieces fit together, and why they are arranged this way. Read this before
[`backend.md`](backend.md) or [`frontend.md`](frontend.md).

## Process model

Three processes, one container image:

```
        ┌─────────────────────────────────────────────┐
        │  nginx  :80                                 │
        │    /        → /static  (built frontend)     │
        │    /api/    → localhost:8000  (prefix       │
        │               stripped by trailing slash)   │
        └──────────────────┬──────────────────────────┘
                           │
        ┌──────────────────▼──────────┐   ┌───────────────────────────┐
        │  uvicorn  :8000             │   │  scheduler worker         │
        │  src.api.app:app            │   │  src.tasks.scheduler_…    │
        │                             │   │                           │
        │  enqueues rows in sync_jobs │──▶│  claims them, runs tasks  │
        └─────────────────────────────┘   └───────────────────────────┘
```

[s6-overlay](https://github.com/just-containers/s6-overlay) is PID 1 and supervises all three.
`/etc/cont-init.d/01-migrations` runs `alembic upgrade head` before anything starts — a failure
there takes the container down rather than serving against a stale schema — and the three
services in `/etc/services.d` come up afterwards, each restarted on its own if it dies. The tree
lives in `cicd/containers/all-in-one/root/`, copied to `/` at build time.

Each service has a `log/run` that pipes it through `s6-log`, which tags every line with `[api]`,
`[scheduler]`, or `[nginx]` — otherwise one container's stream mixes three processes with no way
to tell them apart. The `run` scripts start with `exec 2>&1` because s6 pipes only fd 1 to the
logger, and both uvicorn and Loguru write to stderr. nginx is pointed at `/dev/stdout` and
`/dev/stderr` for the same reason, which also stops it filling `/var/log/nginx` inside the
container, where nothing rotates it.

Two details of that arrangement look like faults and are not. s6 warns at boot that
`/etc/s6-overlay/s6-rc.d` is empty, because the services use the older `services.d` layout — four
shell scripts rather than the sixteen files the `s6-rc` format needs for the same three daemons
and one init step. And `docker stop` reports exit code 137 even when shutdown was orderly, since
s6 ends its own halt sequence with a kill.

`docker-compose.dev.yaml` keeps the same split but gives each process its own container with the
source bind-mounted and reload enabled, and lets the Vite dev server stand in for nginx and the
built bundle — it proxies `/api` with the prefix stripped exactly as nginx does, so the two
environments agree on URLs.

**The API never executes background work.** `POST /tasks/…` writes `sync_jobs` rows and returns
`202` with a `Location` header; the scheduler picks them up within seconds. This keeps the web
process free of implicit schedulers, and means "run now" behaves identically whether it came
from the UI, an operator, or qBittorrent's completion hook.

Consequence worth knowing: the two processes configure Loguru against the same file with
independent rotation state, so records occasionally land in a rotated sibling. The log reader
follows siblings to compensate. See
[`../services/backend/docs/tasks.md`](../services/backend/docs/tasks.md).

## The contract

`openapi.yaml` at the repo root is the single source of truth for the HTTP surface. Three
consumers:

| Consumer | How it uses the spec |
| --- | --- |
| Backend | `tests/api/test_openapi_contract.py` asserts FastAPI's generated spec covers every operation in the document. Pydantic schemas in `src/schemas/` mirror it by hand — there is no Python codegen. |
| Frontend | `npm run codegen` regenerates `src/lib/api/generated/types.ts` with `openapi-typescript`. `src/types.ts` re-exports the schemas the app uses. |
| Mock server | `services/frontend/mock-server/` implements the same document, and serves it at `/openapi.yaml`. |

Note the prefix asymmetry: the spec's `servers` entry is `/api` because that is what nginx
serves under, but FastAPI mounts routes at `/requests`, `/discover`, and so on. The app itself
has no `/api` prefix.

## Backend layers

Dependencies point inward. Nothing in `application/` may import FastAPI, SQLAlchemy models, or
`infrastructure/`.

```
src/
  api/               FastAPI routers, auth dependency, exception handlers.
                     Thin: schema → command → use case → DTO → schema.
  schemas/           Pydantic models at the HTTP boundary. All extend APIModel.
  application/
    use_cases/       One class per operation, grouped by area.
                     commands.py (input) / dto.py (output) / mappers.py / exceptions.py
    interfaces/      Protocols the use cases depend on, plus the record dataclasses
                     those protocols pass around.
    queries/         Read models that bypass use cases (logs, release summary).
    utility/         Torrent name parsing, file matching, language codes, UNSET sentinel.
  infrastructure/    The implementations: sonarr/, radarr/, prowlarr/, qbittorrent/,
                     tvdb/, tmdb/, http/ (BaseHttpClient), logs/ (file reader),
                     and the SQLAlchemy repositories.
  domain/            models.py (ORM entities) and enums.py. No behaviour.
  db/                Declarative Base, DBManager (session/transaction), repository base.
  tasks/             Task step implementations, the scheduler worker, a Typer CLI.
  core/              container.py (DI composition root) and logging.py.
  settings/          AppSettings (pydantic-settings, RELEASARR_ prefix).
```

Two properties this buys, both load-bearing:

**Integrations degrade rather than crash.** Because ports are `Protocol`s, `core/container.py`
can return an in-memory stub when Prowlarr or qBittorrent is unconfigured. The app boots and
the UI works; only grabbing and downloading are inert.

**Use cases are testable without HTTP or a database.** `tests/fakes.py` provides protocol
implementations backed by dicts, so use case tests construct the class directly.

## Frontend structure

Feature-sliced. Each slice owns its endpoints and its React Query keys.

```
src/
  features/
    requests/    api.ts, queries.ts, filtering.ts, useRequestFilters.ts,
                 localization.ts, pages/, components/
    releases/    api.ts, queries.ts, components/, fileMapping/
    discover/    api.ts, queries.ts, keys.ts, pages/, components/
    tasks/       api.ts, queries.ts, pages/  (also hosts useSyncWatcher)
    logs/        api.ts, queries.ts, LogsModal.tsx
  components/    Shared presentational pieces (StatusBadge, Panel, ResponsiveModal, …)
  lib/           api/client.ts (the only fetch wrapper), api/generated/, i18n.ts, queryClient.ts
  utils/         formatters, files, errors, status (the one place status colors live)
  hooks/         useIsMobile
  locales/       resources.ts — en + ru in one file
  router.tsx     Routes, lazy loading, loaders that warm the query cache
  App.tsx        AppShell, nav, useSyncWatcher
```

`queryClient.ts` sets a global `staleTime` of 30s. Polling is deliberately narrow: only
`features/tasks/queries.ts` sets `refetchInterval` (2s for active jobs, 10s for scheduled
tasks). `useSyncWatcher`, mounted once in `AppLayout`, watches those jobs and invalidates
`requestKeys.all` / `releaseKeys.all` when one finishes — which is how a completed background
import shows up in the UI without every page polling.

## How a request flows end to end

1. **`sonarr_sync` / `radarr_sync`** read missing seasons and movies from the *arrs, enrich them
   with TVDB/TMDB metadata, and upsert `media_requests` rows. Uniqueness is
   `(sonarr_series_id, season_number)` for series and `radarr_movie_id` for movies.
2. **A human picks a release.** `GET /releases/search` proxies Prowlarr;
   `POST /requests/{id}/releases/download` hands the magnet or `.torrent` to qBittorrent and
   writes a `releases` row plus a `release_request_links` row. `ReleaseGrabFinalizer` marks the
   request `downloading` and runs the auto-mapper.
3. **`release_sync`** refreshes progress, speeds, seeders, and status from qBittorrent every 30
   seconds. A release becomes `completed` when qBittorrent reports full progress *and* a
   completion timestamp — a finished torrent keeps seeding, so its reported state alone cannot
   be used.
4. **Files get mapped.** `PUT /releases/{id}/files/mapping` stores, per file, a request plus
   (for series) a season and episode. `GET …/mapping/suggestions` offers the auto-mapper's
   guesses; the human confirms or overrides. Saving mappings for an already-finished release
   queues an `export` immediately rather than waiting out the interval.
5. **`export`** takes releases that are finished and not yet exported, resolves the download
   directory from qBittorrent, and calls Sonarr's and Radarr's manual import commands with
   absolute paths. It then asks both apps whether they now hold the request in full, and only
   closes the request if they say yes. Every request the import actually carried files for is
   stamped with an `exported_at`, including the ones that stay open because the release only
   covered part of a season.
6. **`regrab`** re-searches Prowlarr for tracked releases, compares info hashes, and
   re-downloads when the indexer has replaced the torrent (repacks).

Ordering matters: `export` can only import what `release_sync` has already marked completed,
which is why `sync_downloads` queues the two together and in that order.

## Deployment

`.forgejo/workflows/deploy.yml` runs `ruff check ./src` and `ruff format --check ./src`, builds
and pushes the image, then SSHes to pull and restart the compose stack. There is no test or
typecheck step in CI — run `uv run pytest` and `uv run mypy src` locally.
