# Releasarr backend

FastAPI service plus a scheduler worker, built to the contract in
[`../openapi.yaml`](../openapi.yaml). Python 3.12, SQLAlchemy 2.0 async, `uv`.

## Getting started

```bash
uv sync
uv run alembic upgrade head
uv run fastapi dev src/api/app.py
```

The API comes up on `:8001`. Health probes are `/healthz` and `/readyz`; everything else needs
an `X-API-Key` header matching `RELEASARR_API_KEY` (default `dev-secret`).

The scheduler is a **separate process** and is not started by the API. Run it in another
terminal when you need background work:

```bash
uv run python -m src.tasks.cli scheduler
```

Nothing here needs Sonarr, Radarr, Prowlarr, or qBittorrent to boot. Unconfigured integrations
degrade to in-memory stubs or `None`, so the app starts and the API answers; only the parts that
talk to those services are inert. See [`docs/integrations.md`](docs/integrations.md) for exactly
what happens per service.

With no `.env`, the database is SQLite at `./releasarr.db` and logs go to `.logs/backend.log`.

## Commands

| Command | Purpose |
| --- | --- |
| `uv run fastapi dev src/api/app.py` | API with reload on `:8001` |
| `uv run python -m src.tasks.cli scheduler` | The scheduler worker |
| `uv run pytest` | Test suite |
| `uv run pytest tests/api/test_openapi_contract.py` | After any contract change |
| `uv run ruff check ./src` | Lint — what CI runs |
| `uv run ruff format ./src` | Format |
| `uv run mypy src` | Type check |
| `uv run alembic upgrade head` | Apply migrations |
| `uv run alembic revision --autogenerate -m "…"` | Create a migration (then **review it**) |
| `uv run alembic downgrade -1` | Roll back one migration |

One-shot task runs, useful when debugging a sync:

```bash
uv run python -m src.tasks.cli sync-sonarr-requests
uv run python -m src.tasks.cli sync-radarr-requests
uv run python -m src.tasks.cli sync-releases
uv run python -m src.tasks.cli release-summary --json
```

## Layout

```
src/
  api/               Routers, the X-API-Key dependency, exception handlers.
                     Thin: schema → command → use case → DTO → schema.
  schemas/           Pydantic models at the HTTP boundary; all extend APIModel.
  application/
    use_cases/       One class per operation, grouped by area (requests, releases,
                     discover, tasks, logs). commands.py / dto.py / mappers.py /
                     exceptions.py per area.
    interfaces/      Protocols the use cases depend on, plus their record dataclasses.
    queries/         Read models that bypass use cases (logs, release summary).
    utility/         Release-name parsing, file matching, language codes, UNSET sentinel.
  infrastructure/    Adapters: sonarr/, radarr/, prowlarr/, qbittorrent/, tvdb/, tmdb/,
                     http/ (BaseHttpClient), logs/ (file reader), and the repositories.
  domain/            models.py (ORM) and enums.py. No behaviour.
  db/                Base, DBManager (session/transaction), repository base.
  tasks/             Task steps, the scheduler worker, a Typer CLI.
  core/              container.py (DI composition root), logging.py.
  settings/          AppSettings — pydantic-settings, RELEASARR_ prefix.
alembic/versions/    Migrations.
tests/               Mirrors src/, plus conftest.py fixtures and fakes.py.
```

Dependencies point inward: `application/` must not import FastAPI, SQLAlchemy models, or
anything from `infrastructure/`.

## Docs

| Doc | Covers |
| --- | --- |
| [`docs/tasks.md`](docs/tasks.md) | Background tasks, the scheduler, job queueing and collapsing, log filtering, the qBittorrent hook |
| [`docs/integrations.md`](docs/integrations.md) | Every external service: endpoints called, auth, base-URL requirements, retries, degradation |
| [`docs/file-mapping.md`](docs/file-mapping.md) | How release files are listed, parsed, matched to episodes, and imported |

Repo-wide docs live in [`../docs/`](../docs/README.md) — start with
[`../AGENTS.md`](../AGENTS.md) for the conventions, [`../docs/backend.md`](../docs/backend.md)
for the patterns to follow when adding code, and
[`../docs/data-model.md`](../docs/data-model.md) for the schema.

## Configuration

Settings live in `src/settings/config.py`, read from the environment with a `RELEASARR_`
prefix or from `.env`. The full table with defaults is in the
[root README](../README.md#configuration). The ones that catch people out:

- **Base URLs are passed through verbatim** and must already include the provider's API path:
  Sonarr and Radarr `…/api/v3`, Prowlarr `…/api/v1`, qBittorrent `…/api/v2`, TMDB `…/3`.
- **`RELEASARR_API_KEY` fails closed.** An empty server-side key returns 500 rather than
  allowing open access.
- **`RELEASARR_METADATA_LANGUAGES`** is ISO 639-2 three-letter codes, defaulting to
  `("eng", "rus")`, and sets both what metadata gets fetched and the order it is preferred in.
