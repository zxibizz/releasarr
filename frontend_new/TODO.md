# New frontend todos

## API and contract improvements
- Introduce a shared `ErrorResponse` schema and reference it from all `4xx`/`5xx` outcomes so the UI can rely on a predictable `{ code, message, details }` shape (see `openapi.yaml`).
- Document response payloads for async endpoints (`202` on `/requests/{requestId}/releases/download`, `/releases/{id}/pause`, `/releases/{id}/resume`) to clarify whether a body or `Location` header is returned.
- Align write semantics with partial updates: switch `/requests/{requestId}` to `PATCH` (or document full-resource replacement) and add field-level `nullable` hints for optional properties.
- Paginate high-volume collections (`GET /releases`, `/logs`, `/requests/{id}/releases`) and surface `page`, `per_page`, `total` metadata consistently; reflect that in the frontend data model.
- Consolidate request filters so `/requests/{id}/releases` mirrors `/releases?request_id=`; consider deprecating one path to reduce duplication in the client.
- Add reusable component parameters in the spec for paging and filtering (e.g. `#/components/parameters/Page`, `PerPage`, `Status`) to keep documentation DRY and enforce validation.

## Frontend architectural improvements
- Replace ad-hoc data sanitisation helpers inside `useRequests` / `RequestPage` with a shared schema-driven mapper (e.g. Zod) so all fetchers normalise data the same way and runtime validation lives next to the API client.
- Introduce a data-fetching layer (React Query or SWR) to handle caching, refetching, and stale state instead of custom context caches in `useRequests` and `useReleases`.
- Extract log-normalisation logic from `RequestPage` into a dedicated utility and add unit coverage; components should consume already-shaped view models.
- Standardise loading and error UI states via reusable components (skeletons, alerts) to remove duplicated chakra layouts across `RequestsList`, `ReleasesList`, `ReleaseSearch`, etc.
- Move feature-specific code into domain modules (e.g. `features/requests`, `features/releases`) with co-located hooks, components, and tests to improve SOLID separation and testability.
- Align design tokens: replace Tailwind-style class strings in `utils/releaseHelpers.ts` with Chakra theme tokens and extend the theme for status colors.
- Centralise side effects (toast notifications, downloads, refresh triggers) in the feature hooks to keep presentational components pure.
- Add integration tests (React Testing Library + MSW) for request and release flows to guard against regressions during the refactor.

## Step-by-step implementation plan
1. [x] Update `openapi.yaml` with the contract fixes (error schema, response bodies, pagination components, method semantics) and regenerate API typings if applicable.
2. [x] Introduce shared runtime schemas for API entities (`requests.schema.ts`, `releases.schema.ts`) and adapt `apiClient` to decode with them before returning data.
3. [x] Adopt React Query (or similar) and replace `RequestsProvider` / `ReleasesProvider` with query hooks (`useRequestsQuery`, `useRequestQuery`, `useReleasesByRequestQuery`). Preserve existing behaviour with feature flags where needed.
4. [x] Refactor consuming components (`RequestsList`, `RequestPage`, `ReleasesList`, `ReleaseSearch`) to rely on the new hooks, eliminating manual cache mutation and duplicated sanitisation.
5. [x] Move log parsing, release helper utilities, and toast side-effects into domain-specific helpers/hooks; convert components into slimmer presentational layers.
6. [ ] Update theming to expose status color tokens, remove hard-coded class strings, and ensure all status badges/buttons consume theme values.
7. [ ] Backfill unit/integration tests for the new hooks and critical user journeys (list requests, view request detail, queue download) using MSW to assert on the new error contract.
8. [ ] Document the updated architecture in `frontend_new/docs` (data flow, query cache strategy, API contract expectations) so the team can onboard quickly.
