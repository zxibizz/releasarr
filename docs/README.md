# Developer docs

Written for whoever — human or agent — is about to change this code.
[`../AGENTS.md`](../AGENTS.md) is the short version and the entry point; start there.

| Doc | Covers |
| --- | --- |
| [`architecture.md`](architecture.md) | Process model, the OpenAPI contract, backend layers, frontend slices, how a request flows end to end |
| [`backend.md`](backend.md) | Adding endpoints, use case conventions, ports and adapters, the DI container, settings, migrations |
| [`frontend.md`](frontend.md) | Feature slices, the HTTP layer, codegen, routing, i18n, mobile, the mock server |
| [`data-model.md`](data-model.md) | Tables, enums, constraints and the invariants they encode, migration history |
| [`testing.md`](testing.md) | Fixtures, fakes, route tests, frontend render helpers, what is not covered |

Also worth knowing:

- [`../backend/docs/tasks.md`](../backend/docs/tasks.md) — background tasks and the scheduler in
  operational detail: job collapsing, ordering guarantees, log filtering, the qBittorrent hook.
- [`../frontend/README.md`](../frontend/README.md) — frontend scripts and the file-mapping
  internals.
- [`../openapi.yaml`](../openapi.yaml) — the API contract, and the thing to change first.

`screenshots/` holds the images used by the root [`README.md`](../README.md), captured against
the frontend's mock API.
