# Testing

Both suites favour real collaborators over mocks wherever that is cheap: an in-memory SQLite
database instead of a mocked repository, `httpx.MockTransport` instead of a mocked client, the
real Mantine and i18next providers instead of stubs. Mock at the outermost boundary only.

## Backend

`pytest` with `pytest-asyncio` in `asyncio_mode = "auto"`, so `async def test_…` needs no
decorator. Run from `services/backend/`:

```bash
uv run pytest
uv run pytest tests/api/test_openapi_contract.py    # after any contract change
uv run pytest --cov=src
```

Test layout mirrors `src/`:

```
tests/
  api/             Route integration tests, plus the OpenAPI contract test
  application/     Use case, query, and utility tests
  infrastructure/  Client and repository tests
  tasks/           Scheduler and sync task tests
  core/            Container and logging tests
  conftest.py      Shared fixtures
  fakes.py         Protocol implementations for the use case tests
```

### Fixtures

`tests/conftest.py` provides four:

| Fixture | What it gives you |
| --- | --- |
| `api_client` | `httpx.AsyncClient` over `ASGITransport(app=app)` |
| `db_engine` | In-memory SQLite engine with `Base.metadata` applied |
| `session_factory` | `async_sessionmaker` bound to that engine |
| `db_manager` | `DBManager` wrapping it — what repositories take in production |

`captured_records` collects what Loguru would serialize, so assertions can check the structured
fields a log-filtering feature depends on. It is registered at INFO, matching the file sink's
floor, so anything it misses would also be missing from a request's activity view.

### Route tests

Override the route module's `_get_*_use_case` function with a fake, using FastAPI's
`dependency_overrides`. This is the reason those functions exist as named module-level
callables rather than inline lambdas.

```python
API_KEY_HEADER: dict[str, str] = {}  # auth is overridden globally for tests; see conftest.py


class FakeGetUseCase(GetMediaRequestUseCase):
    def __init__(self, dto: MovieRequestDTO | None) -> None:
        self._dto = dto

    async def execute(self, request_id: str) -> MovieRequestDTO:
        if self._dto is None:
            raise MediaRequestNotFoundError(request_id)
        return self._dto


@contextmanager
def override_dependency(dep: Callable[..., Any], value: Any):
    app.dependency_overrides[dep] = lambda: value
    try:
        yield
    finally:
        app.dependency_overrides.pop(dep, None)
```

Fakes subclass the real use case and override `execute`, which keeps the signature honest. Raise
the domain exception from the fake to assert the error mapping, rather than asserting on
`DOMAIN_ERROR_MAP` directly.

### Auth in tests

An autouse fixture in `tests/conftest.py` overrides `get_principal`
(`src/api/dependencies/auth.py`) to a fixed, unrestricted admin `Principal` for every test, so
existing route tests do not have to think about auth — this mirrors the single global API key
the suite used before per-user auth existed. A test exercising the unauthenticated path pops the
override for that one call:

```python
app.dependency_overrides.pop(get_principal, None)
response = await api_client.get("/requests")
assert response.status_code == status.HTTP_401_UNAUTHORIZED
```

For a *restricted* principal (to test ownership scoping or a missing permission), override
`get_principal` with a `Principal` built from a `UserRecord` with the relevant flags unset,
rather than hitting real login. New auth-specific use case tests
(`tests/application/use_cases/auth/`) use the real `Argon2PasswordHasher` and
`JwtAccessTokenCodec` — both are fast and deterministic — against in-memory
`InMemoryUserRepository` / `InMemoryRefreshTokenRepository` fakes, so no fake crypto layer is
needed.

### The contract test

`tests/api/test_openapi_contract.py` finds `openapi.yaml` by walking up from its own file — the
repository root locally, the filesystem root in the dev container, where the service directory is
mounted over `/app` — and asserts FastAPI's generated
spec covers every operation in it. It catches a spec edit that never reached the routes, but not
the reverse, and it does not compare schemas — keeping field names and error codes aligned is
still manual.

### Use case tests

Construct the use case directly with fakes from `tests/fakes.py`. Two kinds live there:

- **Working fakes** hold their state in a dict and record the calls that change it, so a test
  can assert what was asked of Sonarr rather than only what came back.
- **`Unused*` mixins** cover the half of a protocol a test does not exercise. `SonarrService`
  does two jobs — reading what is missing, and managing the library — and a fake for one still
  has to satisfy the whole protocol. The mixins supply the other half and raise
  `NotImplementedError` if it is reached, so an accidental dependency fails loudly instead of
  silently returning a default.

Add to these rather than writing a one-off fake in a test module.

### Infrastructure tests

HTTP clients take a `transport` parameter for exactly this purpose:

```python
client = SonarrHttpClient(
    base_url="http://sonarr/api/v3",
    api_key="key",
    transport=httpx.MockTransport(handler),
)
```

Assert on the recorded requests, not just the parsed result — the mapping from the *arr JSON
shape is usually the thing worth pinning. Repository tests use the `db_manager` fixture against
real SQLite, so constraints are exercised.

## Frontend

Vitest with jsdom and Testing Library. Run from `services/frontend/`:

```bash
npm test
npm run test:watch
```

Tests are colocated with what they test: `Component.test.tsx` next to `Component.tsx`, mobile
variants as `Component.mobile.test.tsx`.

### Setup

`src/test/setup.ts` polyfills what jsdom lacks: `matchMedia` (defaulting to desktop),
`ResizeObserver`, `scrollIntoView`, `document.fonts`.

`src/test/utils.tsx` exports `renderWithProviders`, which wraps the tree in the real
`MantineProvider` (dark, `env="test"`), a fresh `QueryClientProvider`, `ModalsProvider`, and a
`MemoryRouter`. Tests therefore exercise the same provider tree as the app.

```typescript
const { queryClient } = renderWithProviders(<RequestsPage />, { route: '/?status=downloading' });
```

The query client is per-test with `retry: false` and `gcTime: 0`, and is returned so tests can
assert on the cache. i18n is the real instance, so assertions use real English copy — which also
means a missing translation key shows up as a failing test.

### Mocking

Mock `@/lib/api/client`, not the feature's `api.ts`. This keeps `api.ts`, the query keys, and
the hooks under test:

```typescript
vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockResolvedValue({ requests: [movie], total: 1 });
});
```

Spreading `actual` matters: `ApiError` must stay real so error-path tests can construct and
match it.

### Auth in component tests

`renderWithProviders` wraps the tree in the real `AuthContext.Provider`, defaulted to
`TEST_AUTH_VALUE` — an authenticated, unrestricted admin, so a component that calls `useAuth()`
works without extra setup. Pass `auth` to exercise a restricted user or a specific permission:

```typescript
renderWithProviders(<RequestOwner request={request} />, {
  auth: { isAdmin: false, hasPermission: () => false },
});
```

For router guards (`RequireAuth`, `RequirePermission`), render a `<Routes>` tree as the `ui` so
`<Outlet />` has somewhere to go, and set `auth.status` / `auth.hasPermission` per case rather
than mocking `useAuth` — the real context plumbing is what is under test.

**Required-field labels are not exact matches.** Mantine appends a literal ` *` to the label of
any `required` input, so `getByLabelText('Username')` fails — use `getByLabelText(/^username/i)`
or `{ exact: false }`. For a `PasswordInput` specifically, prefer the regex: its
"Toggle password visibility" button's `aria-label` contains "password", so a plain
`{ exact: false }` substring match finds two elements.

### Mobile tests

Separate files, because the assertions are about layout rather than behaviour:

```typescript
describe('RequestsPage on a phone', () => {
  beforeEach(() => {
    setViewportWidth(MOBILE_WIDTH);   // 390
  });

  afterEach(() => {
    setViewportWidth(DESKTOP_WIDTH);  // 1280
  });
});
```

`setViewportWidth` parses Mantine's `(max-width: Xem)` queries against a pixel width so
`useIsMobile` resolves correctly. Always reset in `afterEach` — the polyfill is module-global.

Worth testing at this size: collapsed filter panels, textarea instead of input, whether a long
release name is fully visible, and full-screen modal behaviour.

## What is not covered

- **No end-to-end tests.** No Playwright, no Cypress. The mock server is the closest thing, and
  it is for manual work.
- **No CI test run.** `.forgejo/workflows/deploy.yml` runs only `ruff check` and
  `ruff format --check` on `services/backend/src`. Run `uv run pytest`, `uv run mypy src`, `npm test`,
  and `npm run build` locally before pushing.
- **No schema-level contract checking.** The contract test compares operation lists, not field
  shapes.
