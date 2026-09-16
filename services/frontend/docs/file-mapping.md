# File mapping UI

The mapping editor is the most stateful part of the frontend. It exists because the backend's
matcher deliberately refuses to guess when a filename is ambiguous, so a human has to finish the
job. The backend half — parsing, matching, and import — is documented in
[`../../backend/docs/file-mapping.md`](../../backend/docs/file-mapping.md).

## Pieces

| File                                 | Role                                                |
| ------------------------------------ | --------------------------------------------------- |
| `components/ReleaseDetailsModal.tsx` | The window: General and Content tabs, and edit mode |
| `components/ReleaseGeneralTab.tsx`   | Everything the release row itself knows             |
| `components/ReleaseContentTab.tsx`   | The files and where they are mapped, read-only      |
| `fileMapping/FileMappingForm.tsx`    | Wires the hook to the save mutation                 |
| `fileMapping/FileMappingToolbar.tsx` | Bulk actions                                        |
| `fileMapping/FileMappingRow.tsx`     | One file's request select and season/episode inputs |
| `fileMapping/useFileMappingForm.ts`  | All the state                                       |
| `components/OtherFilesSection.tsx`   | Collapsed non-video files                           |

## The window

A release card's **Details** button opens `ReleaseDetailsModal`, which is two tabs over one
release. **General** is a label/value read of the release row — status, quality, size, tracker
link, info hash, its three dates, the transfer stats, file counts, related requests and the
warnings the card only shows as badges. **Content** is the file list with each file's current
mapping.

The window is titled for what it is, not for which release: the torrent's name is the first line
of **General**, where it sits in full rather than clamped into a dialog header.

The mapping editor is not a tab. `Content` is read-only until **Edit mapping** is pressed, and
the form then replaces the list in place: it is a mode of one tab, so a glance at the files
cannot change anything. Save stores the mappings and hands the list back; Cancel exits too,
asking first when there are unsaved changes. With Mantine's default `keepMounted` both panels
stay mounted, so peeking at General mid-edit does not drop the drafts. Closing the window, or
opening it for another release, resets to General with the list read-only — a render-phase sync
in `ReleaseDetailsModal`, the same shape as the one `useFileMappingForm` keeps itself current
with.

Video files are listed first and non-video files are collapsed, via `splitVideoFiles` in
`utils/files.ts`. Both buckets sort with `compareByFileName`, a `localeCompare` with
`numeric: true`, so `E9` precedes `E10`.

Names are shown without the folder the whole release sits in (`commonRootFolder` and
`withoutRootFolder`, also in `utils/files.ts`). A multi-file torrent names its files
`Root/Season 02/episode.mkv`, so every row repeated the same folder and none of them was told
apart by it; what is left tells the rows apart. The folder is only dropped when **every** file
sits inside the same one — a single-file torrent has none, and a release whose files disagree
has nothing to drop. Only the first segment goes: a season folder inside it stays.

The window does not hold the release it was opened from: `RequestDetailPage` keeps the clicked
release's id and reads the release out of the releases query, so a re-grab that rewrites it — and
swaps its whole file list with the replacement torrent's — shows up in a panel that is already
open. A refresh that re-grabbed anything also invalidates the suggestions query
(`useRefreshRequestReleases`), because the files a proposal was worked out against are gone.

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

An edit made while suggestions were still in flight outranks them — the automap button is the
way to overrule that, see below.

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
| Map automatically                | The stored mappings go, and the automapper's proposals take their place.                                           |

The first targets **video files only**. The second covers every file in the release, because a
subtitle the backend can place belongs on the episode it belongs to.

Automapping is not a patch over what is stored: `automap` starts from a blank draft for every
file and lays the proposals over that, so a file the server proposes nothing for ends up
**unmapped** rather than keeping whatever a human chose for it last time. Nothing is persisted
until Save, so "Undo all changes" is still there to take it back.

The button is held disabled until the proposals have arrived (`isPending` on the suggestions
query). Pressing it earlier would blank the stored mappings, and the proposals landing afterwards
would then leave those rows alone — `withSuggestions` fills in untouched rows only, and these are
no longer untouched.

Mantine clips a Button's label instead of wrapping it (fixed root height, label kept to one
line), so this button carries `styles` freeing both: its label is a sentence, and the Russian one
is longer than a phone's button is wide.

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
