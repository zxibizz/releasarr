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

## Adding New Tasks

1. Implement the task in `src/tasks/` using async functions where you can reuse
   container-provided dependencies.
2. Expose the task helpers from `src/tasks/__init__.py` so they can be imported
   in tests or other tooling.
3. Provide a unit test under `tests/tasks/` that exercises the task logic with
   lightweight fakes for infrastructure dependencies.
4. Document the command invocation in this file so operators can discover it.
