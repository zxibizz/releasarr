# New frontend todos

## Suggested Improvements

- Platform & Tooling
  - [x] Replace CRA with Vite (or Next.js) + SWC to unblock React 19 upgrades, shrink bundles, and enable modern DX (hot-module perf, test runners).
  - [x] Upgrade TypeScript to 5.x, align React typings, and introduce shared ESLint/Prettier config with strict rules for hooks, exhaustive deps, and Chakra best-practices.
  - [x] Add Storybook and Chromatic (or Ladle) for component previews and visual regression safety while iterating on the design system.
  - [x] Generate TypeScript/zod clients from `openapi.yaml` (e.g. with `openapi-typescript` + `orval`/`zodios`) instead of hand-maintaining schemas in `src/types`.

- Architecture & State Management
  - [x] Split `RequestPage` into feature-scoped subcomponents/hooks (detail header, actions, releases, logs, manual search) to reduce the 500+ line monolith and isolate concerns.
  - Convert imperative `useState` clusters on the request detail into a reducer or state machine (XState/Zustand) so manual search and toast lifecycles stay predictable.
  - Co-locate TanStack Query keys and selectors per feature folder, expose typed service layers, and add query/mutation helpers (retry, optimistic updates).
  - Refactor release/request helpers to remove duplicated status/icon utilities and move view logic behind headless presenters.

- Data Fetching & API Layer
- [x] Teach the backend list endpoints to return relationship summaries so `ReleasesList` stops fan-out fetching each related request (batch via `/requests/summary`).
- [x] Add `react-query` prefetch/loaders to route definitions (React Router data APIs) for better suspense support and SSR readiness.
- [x] Centralise error handling with an error boundary + toast utilities, surfacing structured `ApiError` details and guidance.

- UI/UX Enhancements
  - [x] Persist filters/search params for `RequestsList` in the URL, add search, sort toggles, and quick stats (counts per status/type).
  - [x] Replace bare spinners with Chakra skeletons/empty states across remaining views, and introduce background refresh indicators on lists beyond `RequestsList`.
  - [x] Improve accessibility: refresh semantic tokens for contrast, add visible focus outlines, aria labels, and keyboard-friendly flows in modals & mapping forms.
  - Enrich release cards with activity timelines (added/completed) and health badges derived from speed/seeders.

- File Mapping Experience
  - Rebuild `FileRequestMapping` around `react-hook-form` + combobox inputs so large season mappings are fast, undoable, and keyboard friendly.
  - Add smart defaults by parsing filenames once and letting users bulk-apply episodes or auto-map via heuristics before manual tweaks.
  - Virtualise long file lists and surface diff indicators when edits are pending but unsaved.

- Testing & Quality Gates
  - Introduce Vitest (or Jest 29) + Testing Library with MSW for hooks/components, and Playwright smoke paths for critical flows.
  - Enable React Query Devtools and write regression tests for manual search, release actions, and log viewer edge cases.
  - Wire linting/formatting/test checks into CI along with bundle-analyse and Lighthouse badges.

- Documentation
  - Refresh `README.md` to describe the actual hook-based architecture (no more stale provider references) and document local mock server usage.
  - Publish architecture notes per feature (requests/releases/logs) and add contribution guidelines for API schema regeneration.

## Implementation Plan

1. [x] Modernise the toolchain: migrate to Vite (or Next.js) with SWC, upgrade TypeScript/ESLint/Prettier, and configure absolute imports.
2. [x] Automate contract typing: wire `openapi.yaml` into a codegen step that emits clients/zod schemas consumed by hooks and the mock server.
3. [x] Reorganise feature folders: split `RequestPage` into composable modules, move query keys/hooks beside components, and introduce state containers where needed.
4. [x] Enhance the API/services layer: batch related-request lookups, add route loaders/prefetch, and surface consistent `ApiError` messaging through shared utilities.
5. [ ] Polish the UX: add request search/sort with URL sync, swap spinners for skeletons, tighten accessibility, and extend release visuals.
6. [ ] Redesign file mapping: implement form-powered mapping with virtualization, intelligent defaults, and save/undo feedback.
7. [ ] Expand tests and DX tooling: add Vitest/Playwright suites, React Query Devtools, Storybook stories, and CI gates (lint/test/story build).
8. [ ] Update documentation & onboarding guides to reflect the new stack, architecture decisions, and developer workflows.
