# File mapping UI

The mapping editor is the most stateful part of the frontend. It exists because the backend's
matcher deliberately refuses to guess when a filename is ambiguous, so a human has to finish the
job. The backend half — parsing, matching, and import — is documented in
[`../../backend/docs/file-mapping.md`](../../backend/docs/file-mapping.md).

## Pieces

| File                                 | Role                                                |
| ------------------------------------ | --------------------------------------------------- |
| `components/ReleaseFilesModal.tsx`   | Files tab (read-only) and Mapping tab               |
| `fileMapping/FileMappingForm.tsx`    | Wires the hook to the save mutation                 |
| `fileMapping/FileMappingToolbar.tsx` | Bulk actions                                        |
| `fileMapping/FileMappingRow.tsx`     | One file's request select and season/episode inputs |
| `fileMapping/useFileMappingForm.ts`  | All the state                                       |
| `components/OtherFilesSection.tsx`   | Collapsed non-video files                           |

Video files are listed first and non-video files are collapsed, via `splitVideoFiles` in
`utils/files.ts`. Both buckets sort with `compareByFileName`, a `localeCompare` with
`numeric: true`, so `E9` precedes `E10`.

## The draft model

The API models a mapping as a discriminated union on `mapping_type`. That is awkward to edit —
switching a row from movie to series would mean replacing the object — so the hook flattens it:

```typescript
export interface MappingDraft {
  requestId: string;
  requestTitle: string;
  mappingType: MappingType;
  season?: number;
  episode?: number;
}
```

`season` and `episode` are carried for every draft and only serialized back for series
mappings. `draftFromMapping` converts in, `toPayload` converts out.

**Drafts start from stored mappings only.** A file the server has not mapped starts blank, which
is what keeps the unsaved-changes count honest — anything filled in afterwards, including a
server suggestion, is a proposal nobody has agreed to yet and shows as dirty. Dirty is computed
by comparing a draft to `initialDrafts`, not by tracking edit events.

Two render-phase state syncs keep the drafts current without effects: one rebuilds them when the
`files` prop changes (after a save, when the query refetches), and one folds in each new batch of
suggestions. The suggestion sync compares a **content fingerprint** rather than the array
reference, so a parent that rebuilds the array every render does not cause a loop.

Suggestions are laid over untouched rows only:

```typescript
const withSuggestions = (
  drafts: DraftMap,
  initial: DraftMap,
  suggestions: ReleaseFileMappingSuggestion[],
): DraftMap => {
  const next = { ...drafts };

  suggestions.forEach((suggestion) => {
    const current = next[suggestion.file_id];
    const untouched = current && isSameDraft(current, initial[suggestion.file_id] ?? EMPTY_DRAFT);
    if (current && !untouched) {
      return;
    }
    next[suggestion.file_id] = draftFromMapping(suggestion.request_mapping);
  });

  return next;
};
```

An edit made while suggestions were still in flight outranks them. The explicit "use suggested
mapping" button does not — it overwrites every suggested row, edits included.

## Season packs route per season

A complete-series pack holds several seasons, and each season is tracked by its **own request**.
Picking one request for the whole release would therefore be wrong. `buildSeasonIndexes` maps
each series to a `season → request` index, keyed by Sonarr id where available and falling back
to a normalized series title for requests that predate a Sonarr link.

`seriesDraft` then resolves a file's request from its season rather than from whatever request
the user clicked, which is why "apply request to all" on a series is really "apply this _series_
to all" — each file still lands on the request owning its own season.

## Toolbar actions

| Action                           | Semantics                                                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Apply request to all video files | Movie: every video file gets that request. Series: each file keeps its season and routes through the season index. |
| Use suggested mapping            | Overwrites all suggested rows, **discarding edits to them**.                                                       |
| Number episodes in order         | Fills empty episode numbers in name order.                                                                         |
| Reset changes                    | Back to the stored state.                                                                                          |

All of them target **video files only**.

Numbering deserves a note, because it is the escape hatch for releases the backend cannot parse
at all:

```typescript
const episode = draft.episode ?? (lastEpisode.get(season) ?? 0) + 1;
lastEpisode.set(season, Math.max(lastEpisode.get(season) ?? 0, episode));
```

Counters are **per season**, rows that already have an episode keep it and raise the high-water
mark, and only empty rows get filled. So numbering a half-mapped season continues from the
highest number already there instead of renumbering from one.

`reset` also bumps a `resetToken`, which the row components use to drop uncontrolled input
state that would otherwise survive the reset.

## Saving

`buildPayload` maps drafts through `toPayload` and drops the nulls. Two things are deliberately
not sent:

```typescript
const toPayload = (fileId: string, draft: MappingDraft): ReleaseFileMappingInput | null => {
  if (!draft.requestId) {
    return null;
  }

  if (draft.mappingType === 'series') {
    // Guessing 1 here would persist a wrong episode; leave the file unmapped instead.
    if (!draft.season || !draft.episode) {
      return null;
    }
```

A file with no request, and a series file missing a season or episode, are both omitted rather
than guessed at. An empty payload shows a "nothing to save" notification instead of firing a
request.

The save `PUT`s to `/releases/{id}/files/mapping` and then invalidates releases-by-request,
the mapping suggestions, and task jobs — jobs because the backend may have queued an export in
response (it does, for any `COMPLETED` release). Errors surface the `ApiError` message in a red
notification.

## Two known gaps

**Unmapping does not persist.** The request select is clearable and clearing it blanks the
draft, but a draft with no `requestId` returns `null` from `toPayload` and is dropped from the
payload. The backend accepts `mapping_type: null` to clear a mapping; the UI has no way to send
it. Clearing a row therefore looks like it worked until the query refetches.

**The video extension lists have drifted.** The frontend knows 8 extensions, in
`utils/files.ts`:

```typescript
const VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'];
```

The backend's `release_parsing.VIDEO_EXTENSIONS` also includes `.ts`, `.m2ts`, `.mpg`, `.mpeg`,
`.ogm`, and `.rmvb`. A release of `.ts` files gets auto-mapped by the backend but is filed under
"other files" in the UI, and the bulk actions — which only touch the video bucket — skip it.
Keep the lists in step when touching either.
