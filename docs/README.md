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

The docs above are repo-wide. Detail that only concerns one side lives next to the code:

| Doc | Covers |
| --- | --- |
| [`../backend/README.md`](../backend/README.md) | Backend setup, commands, layout, configuration gotchas |
| [`../backend/docs/tasks.md`](../backend/docs/tasks.md) | Background tasks and the scheduler: job collapsing, ordering guarantees, log filtering, the qBittorrent hook |
| [`../backend/docs/integrations.md`](../backend/docs/integrations.md) | Sonarr, Radarr, Prowlarr, qBittorrent, TVDB, TMDB — endpoints called, auth, retries, degradation |
| [`../backend/docs/file-mapping.md`](../backend/docs/file-mapping.md) | Release-name parsing, the file matcher, auto-mapping, import |
| [`../frontend/README.md`](../frontend/README.md) | Frontend setup, scripts, routing, i18n, mobile |
| [`../frontend/docs/file-mapping.md`](../frontend/docs/file-mapping.md) | The mapping editor's state model and bulk actions |
| [`../frontend/docs/mock-server.md`](../frontend/docs/mock-server.md) | The mock API and how to extend it |

[`../openapi.yaml`](../openapi.yaml) is the API contract, and the thing to change first.

`screenshots/` holds the images used by the root [`README.md`](../README.md), captured against
the frontend's mock API.
