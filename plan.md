---
name: Requests page episode counts
overview: Drop the "Created …" line from request cards and replace it, for series, with downloaded / pending / not-aired episode counts persisted on `media_requests` during the Sonarr sync.
todos:
  - id: migration
    content: Add alembic migration for aired_episodes / downloaded_episodes on media_requests (down_revision e1f36b8ac704)
    status: pending
  - id: model-interfaces
    content: Add the two columns to domain/models.py, MediaRequestRecord, CreateMediaRequestData, UpdateMediaRequestData, and the SQLAlchemy repository
    status: pending
  - id: sync
    content: Populate the counts in sync_sonarr._sync_season and clear pending in _mark_completed
    status: pending
  - id: dto-schema
    content: Add SeriesEpisodeCountsDTO + derivation in mappers.py, SeriesEpisodeCounts pydantic schema, and episode_counts on SeriesRequest
    status: pending
  - id: openapi
    content: Update openapi.yaml with SeriesEpisodeCounts and the nullable episode_counts property, then run npm run codegen
    status: pending
  - id: status-colors
    content: Move episode status colors from SeasonEpisodes.tsx into utils/status.ts as EPISODE_STATUS_COLOR
    status: pending
  - id: card
    content: Remove the createdAt footer from RequestCard and render the three count badges for series
    status: pending
  - id: i18n-mock
    content: Update en/ru locale keys and add episode_counts to the mock server series requests
    status: pending
  - id: tests-docs
    content: Update backend and frontend tests, refresh docs/data-model.md, run linters and the openapi contract test
    status: pending
isProject: false
---

# Requests page: drop dates, add series episode counts

## What exists today

The requests list is a card grid, not a table. `[RequestCard.tsx](services/frontend/src/features/requests/components/RequestCard.tsx)` renders exactly one date, in its footer:

```89:91:services/frontend/src/features/requests/components/RequestCard.tsx
          <Text size="xs" c="dimmed" mt="auto">
            {t('requestCard.createdAt', { date: formatDate(request.created_at) })}
          </Text>
```

`updated_at` is in the contract but never rendered anywhere in the requests UI, so nothing to remove for it. Per your choice, `created_at`/`updated_at` stay in the API and the "Newest first"/"Oldest first" sort keeps working.

There is no episodes table. The only episode data persisted for a series request is `total_episodes`. But the Sonarr sync already fetches season statistics that contain everything needed:

```24:32:services/backend/src/application/interfaces/sonarr.py
@dataclass(slots=True)
class SeriesSeasonDetails:
    """Detailed information about a Sonarr season."""

    season_number: int
    episode_count: int
    total_episode_count: int
    episode_file_count: int
    monitored: bool = False
```

`_sync_season` in `[sync_sonarr.py](services/backend/src/application/use_cases/requests/sync_sonarr.py)` already reads `season_info` and persists only `total_episode_count`. The other two numbers are discarded.

```mermaid
flowchart LR
  sonarrStats["Sonarr season statistics"] --> sync["_sync_season"]
  sync --> cols["media_requests: total_episodes, aired_episodes, downloaded_episodes"]
  cols --> mapper["record_to_dto derives counts"]
  mapper --> api["SeriesRequest.episode_counts"]
  api --> card["RequestCard footer badges"]
```



## Data design

Persist two new nullable integer columns rather than three derived ones, so the stored facts stay non-redundant against the existing `total_episodes`:

- `aired_episodes` <- `season_info.episode_count`
- `downloaded_episodes` <- `season_info.episode_file_count`

Derived at the mapper, clamped to be non-negative:

- downloaded = `downloaded_episodes`
- pending = `aired_episodes - downloaded_episodes`
- not aired = `total_episodes - aired_episodes`

Nullable so rows that predate the migration report `episode_counts: null` instead of a misleading "everything unaired", and the card simply omits the line until the next sync fills it in.

## Backend

1. **Migration** `services/backend/alembic/versions/<rev>_add_media_request_episode_counts.py`, `down_revision = "e1f36b8ac704"` (current head). Two nullable `sa.Integer()` columns added via `op.batch_alter_table("media_requests")`, matching the style of `[2f6a6434600c_add_sonarr_series_column.py](services/backend/alembic/versions/2f6a6434600c_add_sonarr_series_column.py)`. No enum change, so `batch_alter_table` is safe here.
2. **Model** `[services/backend/src/domain/models.py](services/backend/src/domain/models.py)`: add `aired_episodes` and `downloaded_episodes` to `MediaRequest`, next to `total_episodes`. Leave `ck_media_requests_movie_series_fields` alone — the new columns are null for movies without needing a constraint change.
3. **Interfaces** `[media_requests.py](services/backend/src/application/interfaces/media_requests.py)`: add the two fields to `MediaRequestRecord`, `CreateMediaRequestData`, and `UpdateMediaRequestData` (the latter defaulting to `UNSET`).
4. **Repository** `[repository.py](services/backend/src/infrastructure/media_requests/repository.py)`: pass them in `create_request` and read them in `_to_record`. `update_request` iterates `fields(UpdateMediaRequestData)` and needs no change.
5. **Sonarr sync** `[sync_sonarr.py](services/backend/src/application/use_cases/requests/sync_sonarr.py)`: in `_sync_season`, take the two counts off `season_info` alongside the existing `total_episodes`. In `_mark_completed`, also set `downloaded_episodes = record.aired_episodes`, so a season that has left Sonarr's missing list does not keep advertising pending episodes.
6. **DTO + mapper**: new `SeriesEpisodeCountsDTO(downloaded, pending, unaired)` in `[dto.py](services/backend/src/application/use_cases/requests/dto.py)`, and `SeriesRequestDTO.episode_counts: SeriesEpisodeCountsDTO | None`. `[mappers.py](services/backend/src/application/use_cases/requests/mappers.py)` does the derivation, returning `None` when `aired_episodes` is null.
7. **Schema** `[schemas/requests.py](services/backend/src/schemas/requests.py)`: `SeriesEpisodeCounts` model and `episode_counts: SeriesEpisodeCounts | None = None` on `SeriesRequest`. The route already does `SeriesRequest.model_validate(dto)`, so the nested dataclass maps through with no route change.
8. `**openapi.yaml**` (contract first, before codegen): new `SeriesEpisodeCounts` schema and a nullable `episode_counts` property on `SeriesRequest`.

## Frontend

1. **Codegen**: `npm run codegen` from `services/frontend/` to refresh `src/lib/api/generated/types.ts`.
2. **Shared colors**: episode status colors currently live in a local map inside `[SeasonEpisodes.tsx](services/frontend/src/features/requests/components/SeasonEpisodes.tsx)`, which the card now needs too. Move it to `[utils/status.ts](services/frontend/src/utils/status.ts)` as an exported `EPISODE_STATUS_COLOR` and import it in both places, keeping the one-place rule intact (`downloaded` teal, `missing`/pending yellow, `unaired` gray).
3. `**RequestCard.tsx**`: delete the `createdAt` footer `Text` and the now-unused `formatDate` import. In its place, for `request.type === 'series'` with a non-null `episode_counts`, render a compact footer row of three small badges; movies keep an empty footer so card heights stay even in the grid.
4. **i18n** `[resources.ts](services/frontend/src/locales/resources.ts)`: remove `requestCard.createdAt` from `en` (line 50) and `ru` (line 670); add `requestCard.episodes.{downloaded,pending,unaired}` to both, with `_one`/`_other` for English and `_one`/`_few`/`_many`/`_other` for Russian.
5. **Mock server** `[mockData.ts](services/frontend/mock-server/mockData.ts)`: add `episode_counts` to the series requests, leaving one without it so the null path is exercised in the mock UI.

## Tests and docs

1. Backend: extend the `sync_sonarr` tests to assert the counts are written on create/update and zeroed-out on the completion transition; update any media-request repository/mapper fixtures; run `uv run pytest tests/api/test_openapi_contract.py`.
2. Frontend: update `RequestsPage.test.tsx` / `RequestsPage.mobile.test.tsx` fixtures and assert the badges render for a series and not for a movie.
3. Update the `media_requests` column list in `[docs/data-model.md](docs/data-model.md)`.
4. Run `uv run ruff check ./src`, `uv run mypy src`, and `npm run lint` / `npm run build`.

