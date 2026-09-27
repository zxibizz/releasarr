# Contributing to Releasarr

Thanks for taking an interest. Releasarr sits between someone's indexers, their
download client and their library, so a bug here tends not to produce a stack
trace — it produces the wrong episode imported, or a torrent nobody asked for.

## Before you start

Read [AGENTS.md](AGENTS.md). It is short, and it is the actual contract: the
layering rules, the API-contract workflow, and the handful of invariants that
review enforces. Then read whichever of [docs/backend.md](docs/backend.md) and
[docs/frontend.md](docs/frontend.md) matches the half you are touching.

## Development setup

```sh
git clone https://github.com/zxibizz/releasarr.git
cd releasarr
make setup          # uv sync + npm ci
```

You need [uv](https://docs.astral.sh/uv/), Python 3.12 and Node 22.

The loop:

```sh
make check          # everything CI runs, both halves
make test-backend   # just pytest
make test-frontend  # just vitest
```

For UI work without a backend, `npm run dev:mock` in `services/frontend/` serves
the mock API alongside Vite. For the whole stack with hot reload on both sides,
`docker compose -f docker-compose.dev.yaml up --build`.

### The API contract

[`openapi.yaml`](openapi.yaml) is the single source of truth for the HTTP API
and changes first. An API change touches four places, and CI fails if they
disagree:

1. `openapi.yaml`
2. the backend schemas in `services/backend/src/schemas/` (checked by
   `tests/api/test_openapi_contract.py`)
3. the frontend types — run `make codegen`, never edit
   `services/frontend/src/lib/api/generated/types.ts` by hand
4. the mock server in `services/frontend/mock-server/`

## The rules that will get a PR sent back

They are explained in full in [AGENTS.md](AGENTS.md).

- **Dependencies point inward.** `application/` never imports FastAPI,
  SQLAlchemy models or `infrastructure/`; use cases depend on Protocols in
  `application/interfaces/`.
- **Route handlers stay thin.** Domain exceptions are mapped in
  `DOMAIN_ERROR_MAP`, not caught in routes.
- **Background work never starts inside the API.** The API writes a
  `sync_jobs` row; the scheduler claims it.
- **Every route declares a guard**, and a single-request read is checked
  against the caller's request scope.
- **All frontend HTTP goes through `apiRequest`.**
- **UI strings go into both `en` and `ru`.**
- **Logging is loguru via `get_logger(LogComponent.…)`**, with context as
  keyword arguments. Never an f-string.
- **Comments explain why, not what.**

## Database changes

Schema changes need a migration:

```sh
cd services/backend
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Read the generated file before committing it. Autogenerate does not handle
Postgres enum changes — those need hand-written SQL — and `batch_alter_table`
silently does nothing on Postgres. [docs/data-model.md](docs/data-model.md)
covers both. Releasarr runs on SQLite and Postgres, and CI migrates both.

## Pull requests

- One topic per PR.
- `make check` green; CI runs the same checks plus the image build.
- New behaviour comes with a test. Bug fixes come with the test that fails
  without the fix.
- Add a line to the `Unreleased` section of [CHANGELOG.md](CHANGELOG.md).
- Update the configuration tables in [README.md](README.md) if you add an
  environment variable.

## Releasing

The version lives in several files and is pinned as an image tag in the docs;
CI refuses a tag that disagrees with any of them, so never bump by hand:

```bash
python3 .github/scripts/bump_version.py 1.2.3
```

That rewrites all of them, retitles `Unreleased` as the new release and moves the
CHANGELOG links. Read the section it opened — it becomes the release notes
verbatim — then commit and tag that commit:

```bash
git commit -am "Release v1.2.3"
git tag -a v1.2.3 -m v1.2.3
git push origin master v1.2.3
```

A release candidate is cut from the bumped commit without a further bump:
`v1.2.3-rc1` is accepted against sources that say `1.2.3`, publishes the `beta`
image tag, and never moves `latest`.

## Reporting bugs

Open an issue with the bug template. The most useful things you can include are
the output of `GET /api/v1/system/status` and the logs from **System → Logs** around the
problem.

Security issues go to [SECURITY.md](SECURITY.md) instead, not to the issue
tracker.
