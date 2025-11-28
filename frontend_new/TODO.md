# New frontend todos

## Critical Functionality

- [ ] `frontend_new/src/components/RequestPage.tsx:133` Wire the “Refresh Status” card into useRequest().refetch and trigger a paired releases refetch, with optimistic UI and toast feedback.
- [ ] `frontend_new/src/components/RequestPage.tsx:139` Replace the manual search placeholder with the real backend trigger (per OpenAPI) and surface success/error states to the user.
- [ ] `frontend_new/src/components/ReleasesList.tsx:23` Implement pause/resume handlers that call the existing API methods (expose them from services/api.ts) and pass them through to ReleaseCard.
- [ ] `frontend_new/src/components/ReleaseFilesModal.tsx:147` Preserve updated file mappings locally (or refetch the release) instead of the current no-op onMappingUpdate.

## Error Handling & Resilience

- [ ] `frontend_new/src/services/api.ts:15` Harden the fetch wrapper: detect non‑JSON success bodies, map HTTP status codes to actionable errors, and add optional abort support.
- [ ] `frontend_new/src/hooks/useRequests.ts:14` Guard against malformed payloads (missing requests, unexpected types) before mutating state so the UI can fall back gracefully.
- [ ] `frontend_new/src/components/ReleaseCard.tsx:353` Protect against undefined release files/numeric fields from the backend by adding safe defaults and defensive formatting.
- [ ] `frontend_new/src/components/RequestPage.tsx:210` Allow RequestLogsModal to cope with snake_case keys or missing timestamps by normalising data on load.

## UX & Interaction

- [ ] `frontend_new/src/components/FileRequestMapping.tsx:101` Surface loading/error states from useRequests() so the mapping UI doesn’t render empty dropdowns without context.
- [ ] `frontend_new/src/components/RequestPage.tsx:224` Auto-scroll or focus the manual search area when prompted and debounce repeated shake animations for accessibility.
- [ ] `frontend_new/src/components/ReleasesList.tsx:155` Replace destructive browser alerts with Chakra toasts/confirmations for mapping validation and delete flows.

## Architecture & Refactoring

- [ ] `frontend_new/src/utils/formatters.ts:1` Deduplicate the two formatFileSize implementations (and related helpers) into a single utility module.
- [ ] `frontend_new/src/hooks/useReleases.ts:119` Lift request/release fetching into a shared data layer (React Query/SWR or context) so Request cards, mapping, and modals work off one cache.
- [ ] `frontend_new/src/App.tsx:39` Add a Route path="*" 404 view and consider splitting navigation/layout shells from routing for future sections.

## Cleanup, Docs & Tests

- [ ] `frontend_new/src/components/RequestPage.tsx:269` Remove remaining alert placeholders after toasts are in place.
- [ ] `frontend_new/src/index.tsx:32` Prune CRA scaffolding comments (and similar boilerplate in setupTests.ts, services/api.ts) as part of a formatting pass.
- [ ] `frontend_new/src/App.test.tsx:5` Replace the default “learn react” test with focused render tests for RequestsList/RequestPage; extend coverage to hooks (error paths, filters).
- [ ] `frontend_new/README.md:1` Update the README to match the Chakra-based implementation, document the mock server workflow, and call out required env vars.