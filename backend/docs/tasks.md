# Operational Tasks

The new backend ships with standalone async tasks that reuse the shared
container and infrastructure wiring. These tasks can be executed alongside the
FastAPI app using `uv run`.

## Release Summary

Outputs a JSON payload describing how many releases exist in the system grouped
by status. Useful for dashboards or smoke checks during operations.

```bash
uv run python -m src.tasks.cli release-summary --json
```

Without `--json`, the command prints a human-readable summary instead.

The task relies on the same database configuration specified in the
`AppSettings`, so ensure environment variables are set before running it.

## Sync Sonarr Requests

Imports Sonarr missing seasons into media requests (enriched with TVDB
metadata when configured).

```bash
uv run python -m src.tasks.cli sync-sonarr-requests
```

## Sync Releases

Refreshes release download stats (progress, speeds, seeders, status) from
qBittorrent. Requires the `RELEASARR_QBITTORRENT_*` environment variables.

```bash
uv run python -m src.tasks.cli sync-releases
```

## Background Scheduler (separate worker)

Runs the Sonarr sync, release sync, export, and regrab tasks on a loop. This is
a standalone worker process and is deliberately NOT started inside the FastAPI
app, keeping the web process free of implicit background schedulers. Run it
alongside the API under your process manager (systemd, Kubernetes, etc.):

```bash
uv run python -m src.tasks.cli scheduler
# equivalent to:
uv run python -m src.tasks.scheduler_service
```

It reuses the shared application container, so it picks up the same settings,
logging, and (single, shared) qBittorrent client as the API.

## Adding New Tasks

1. Implement the task in `src/tasks/` using async functions where you can reuse
   container-provided dependencies.
2. Expose the task helpers from `src/tasks/__init__.py` so they can be imported
   in tests or other tooling.
3. Provide a unit test under `tests/tasks/` that exercises the task logic with
   lightweight fakes for infrastructure dependencies.
4. Document the command invocation in this file so operators can discover it.
