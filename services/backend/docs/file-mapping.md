# File mapping

Sonarr and Radarr need to be told which file in a torrent is which episode. Releasarr guesses,
then lets a human correct the guess. This is the subsystem that does the guessing, and it is the
one most likely to need tuning when a release group invents a new naming scheme.

The editing UI is documented in [`../../frontend/docs/file-mapping.md`](../../frontend/docs/file-mapping.md).

## The pipeline

1. **Grab** parses the `.torrent` and writes a `release_files` row per file
   (`use_cases/releases/grab.py`).
2. **Auto-map** runs immediately after the grab and persists whatever it can work out
   (`ReleaseAutoMapper.apply`).
3. **Suggestions** re-run the same matcher on demand for the mapping UI, persisting nothing
   (`suggest_file_mappings.py`).
4. **A human** edits and saves, which validates and persists and may re-queue an export
   (`update_file_mappings.py`).
5. **Export** runs the matcher once more to fill any gaps, then imports
   (`export_finished.py`).
6. **A re-grab** reads the replacement torrent's own file list and reconciles the stored rows with
   it (`ReleaseRegrapper.regrab` — see [Re-grabbing a release](#re-grabbing-a-release)).

The matcher runs three times over a release's life. It must therefore be idempotent and must
never clobber a hand correction — see [What survives a re-run](#what-survives-a-re-run). The
re-grab pass is the fourth, and it is deliberately narrow: it may only write the files that
replacement added.

## Where files come from

Only from a parsed `.torrent`. `parse_torrent` (`utility/torrent.py`) reads the file list via
`torrentool`, and `to_release_files` turns each entry into a row with `path` initially equal to
`name`:

```python
def to_release_files(files: Sequence[TorrentFileInfo]) -> list[ReleaseFileRecord]:
    """Turn a torrent's file list into unmapped release file records."""

    return [
        ReleaseFileRecord(
            id=str(uuid4()),
            name=file.name,
            size_bytes=file.size_bytes,
            path=file.name,
            mapping=None,
        )
        for file in files
    ]
```

**A magnet-only grab produces no file rows at all.** `parse_magnet` can recover an info hash and
a display name, but a magnet link carries no file list, and nothing back-fills the rows from
qBittorrent. Both `queue_release_download.py` and `queue_manual_release.py` pass `files=None` in
that case, and the mapping UI stays empty: if you are wondering why a release cannot be mapped,
check whether it was grabbed from a magnet. The one later source of a file list is a re-grab,
which reads the replacement's own `.torrent` when the indexer serves one — see
[Re-grabbing a release](#re-grabbing-a-release).

Rows are inserted at `create_release`, when the file list is non-empty, and by that re-grab — the
only path that adds files to a release which already exists.

## Re-grabbing a release

A re-grab writes over the release row it replaces: same id, new info hash, and the
`last_exported_info_hash=None` re-arm that puts the release back on the export queue. The stored
files have to follow it, since the export imports by their paths.

`reconcile_release_files` (`utility/torrent_files.py`) matches them against the replacement's own
file list — exact relative path first, then the basename when both sides carry the same number of
files under it, which is how a repack that renamed only the torrent's root keeps its mappings:

| Case                                     | What happens                                                                                              |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| A stored file the torrent still carries  | The row is repointed at the new name, size and path, and keeps **every** mapping column                   |
| A file only the torrent has              | Inserted unmapped, then automapped on its own (`ReleaseAutoMapper.apply_to`)                              |
| A stored file the torrent does not carry | The re-grab is refused outright — nothing queued, nothing written — with a `regrab_files_missing` warning |

That last rule is why the file list is read before anything is queued: a replacement that dropped
a file would leave the release describing something that was never downloaded, and the export
would try to import a path that does not exist.

The refusal is also what takes the release out of the sweep: `get_potential_outdated_releases`
excludes any release holding a `regrab_files_missing` row, because the indexer's answer will not
change between two passes and each check costs a search plus the torrent file it downloads to
compare files. The on-demand refresh on the request still checks it — that is the retry path — and
a replacement that finally carries every stored file clears the row and puts the release back in
the sweep.

Only the added files are automapped. Everything else was resolved once — by hand or by the grab —
and re-deriving a mapping nobody asked to change is how a correction gets lost, which is why
`apply_to` takes the file ids it may write for instead of running `apply` over the release.

A replacement whose file list cannot be read — a magnet-only result, or a torrent file that would
not fetch or parse — is downloaded anyway, with the stored rows left alone and a warning in the
release's request log. No warning row is written in that case: an answer nobody got disproves
nothing, the same rule `release_not_listed` follows.

When the added files map to nothing at all, the release carries `regrab_files_unmapped` naming
those files, so a human can be asked for them. Saving mappings that place every one of them
clears the row (`UpdateReleaseFileMappingsUseCase`), and so does a later re-grab that places one.

## Parsing a name

`utility/release_parsing.py`. No external parser; a cascade of regexes tried strongest-first.

Season and episode together, in precedence order:

| Pattern                          | Matches                                                      |
| -------------------------------- | ------------------------------------------------------------ |
| `s(\d{1,3})[\s._-]*e(\d{1,3})`   | `S01E02`, `s2e7`                                             |
| `season\s*N\s*(episode\|ep)\s*N` | `Season 2 Episode 5`                                         |
| `(\d{1,2})x(\d{1,3})`            | `2x05` — the trailing `(?![\dip])` is what stops `1920x1080` |

Then season-only (`Season 2`, `S2`, `Saison 3`, `Temporada 3`) from the filename stem or, failing
that, by walking parent directories in reverse. Then episode-only (`Episode 5`, `ep5`, `e5`).

`parse_episode` runs these in order, removing matched text as it goes, and validates the result
(season `0..100`, episode `1..999`). A `season_hint` unlocks looser reading but is never
_returned_ as the parsed season, so a hint can never be mistaken for evidence.

### The loose pass, and why it needs a junk filter

Absolute-numbered anime releases look like `[Group] Show - 07 [1080p].mkv` — a bare number and
nothing else. `_LOOSE_EPISODE_PATTERN` will read that, but only when the season is already known
and only if **exactly one** candidate number survives. Two bare numbers is ambiguous and returns
nothing.

A release title containing its own number (`Show Name 2 - 01.mkv`) ties that number against the
real episode in every file of the pack alike, which would otherwise leave the whole pack
unreadable. `ReleaseFileMatcher` works around this per directory: `loose_episode_candidates`
exposes the raw candidate set, and `parse_episode`'s `ignore_title_numbers` lets a caller
discount whatever number every file in the folder has in common before checking for a single
survivor. Discounting is only ever a tie-breaker — when it would empty the set the original
wins, so a name whose real episode number happens to match still resolves.

For this to work, quality tokens have to be stripped first, which is what `_RELEASE_TAGS` and
`_JUNK_PATTERN` are for: resolutions (`1080p`, `1920x1080`), codecs (`x265`, `hevc`, `10bit`),
audio (`ddp`, `atmos`, channel layouts), sources (`web-dl`, `bluray`, `amzn`), meta (`repack`,
`proper`, `v2`), and four-digit years. Without it, `1080p` becomes episode 1080 and `2005`
becomes episode 5.

**The junk filter only applies to the loose pass.** An explicit `S01E02` is trusted as-is. So
when adding a tag to that list you cannot break explicit parsing, which makes it a safe place to
extend. `tests/application/utility/test_release_parsing.py` pins the cases that used to break.

### Movies

`normalize_title` reduces a title to alphanumerics for comparison, Unicode-safe.
`movie_titles` yields candidates from the segment before the first release tag, plus folder
names, and handles the trailing-year ambiguity that makes `Blade Runner 2049` hard.
`parse_year` takes the last `(19|20)\d{2}` in the filename, then in the folders.

`natural_sort_key` splits on digit runs so `E9` sorts before `E10`. Ordering matters to the
matcher, so use it rather than a plain sort.

## Matching files to requests

`utility/file_matcher.py`. There is **no scoring** — it is a chain of precedence rules, which
makes it predictable and testable but means new heuristics have to be slotted in at the right
priority rather than given a weight.

Files are processed in natural-sort order, series first (video files only), then movies over
whatever is left.

```python
hint = self._first_of(
    mapping.season if mapping else None,
    context.seasons.get(directory),
    sole_season,
)
parsed = parse_episode(file.name, file.path, season_hint=hint)

season = self._first_of(mapping.season if mapping else None, parsed.season, hint)
...
episode = self._first_of(
    mapping.episode if mapping else None,
    parsed.episode,
    previous + 1 if previous is not None else None,
)
```

Season precedence is **existing mapping → parsed from name → directory or sole-season hint**.
Episode precedence is **existing mapping → parsed → the previous file's episode plus one**.

That last fallback is how season packs with untitled extras get numbered: within a
`(directory, season)` context, a file with no parseable number continues the sequence from the
file before it in natural-sort order.

`sole_season` is the anime case — when exactly one season appears among the candidate requests,
it becomes the hint that lets the loose pass read a bare `07`.

Requests are indexed by `season_number`, and a file's season decides which request it belongs
to. If a file's season has no request but the file already had a `request_id`, the request is
kept and only the season and episode are updated; this is what repairs a pack that was grabbed
against a single season's request. With neither, the file is skipped.

Movies:

| Case                          | Behaviour                                       |
| ----------------------------- | ----------------------------------------------- |
| One movie request, many files | Map only the **largest file by size**           |
| Several movie requests        | Match on normalized title from `movie_titles()` |
| Colliding titles (a remake)   | Disambiguate on `parse_year` vs `request.year`  |
| Colliding titles, no year     | Leave unmapped                                  |

Title matches must be complete, so `Iron Man 2` does not claim `Iron Man`'s files.
`tests/application/utility/test_file_matcher.py` covers 20-odd of these, including
`Ocean's 8` not being read as season 8.

## What survives a re-run

Because the matcher runs at grab, on every suggestion request, and again at export:

- **Hand-set `season` and `episode` are preserved** — they sit first in the precedence chain.
- **`request_id` is always re-derived** from the season. Deliberate: it is what fixes a pack
  grabbed against one season's request.
- Non-video files, unrequested seasons, and ambiguous bare numbers are skipped rather than
  guessed at.
- A file whose name clearly contains a season _and_ episode but which could not be resolved does
  **not** fall through to the movie pass.

`ReleaseAutoMapper.apply` persists only files whose mapping actually changed, so a re-run over
an already-correct release is a no-op write. `suggest` does the same work without persisting,
and returns only the files it _would_ change — which is why an already-correct release returns
an empty suggestion list rather than confirming every file.

`ReleaseAutoMapper` also widens the candidate request set before matching: sibling seasons of
the same Sonarr series that appear in the files but are not yet linked to the release, and — if
the release has any movie request at all — every outstanding Radarr movie request, so
collection packs can be split across movies.

## Saving an edit

`update_file_mappings.py` validates that each `file_id` belongs to the release
(`ReleaseFileNotFoundError` → 404), that a `mapping_type` comes with a `request_id`, and that a
series mapping carries both season and episode (`ValueError` → 400). `domain/models.py` backs
this up with a check constraint, so a series row without season and episode cannot exist:

```python
CheckConstraint(
    "(mapping_type != 'series') OR (season IS NOT NULL AND episode IS NOT NULL)",
    name="ck_release_files_series_mapping",
),
```

If the mapped request is not yet linked to the release, the repository appends it.

Saving then **re-arms the export**, which is the non-obvious part:

```python
await self._repository.update_release(
    command.release_id,
    last_exported_info_hash=None,
    export_failures_count=0,
)
```

Clearing `last_exported_info_hash` makes an already-exported release eligible again, and
zeroing the failure count gives it a fresh five attempts. If the release is `COMPLETED`, an
`EXPORT` job is queued immediately with trigger `API` so the fix applies without waiting for the
scheduler. A still-downloading release is left alone — export runs on completion anyway. A
failure to queue is logged but does not fail the save.

Passing `request_mapping: null` for a file clears its mapping; leaving the file out of the
`files` list leaves whatever it has. The contract says so
(`ReleaseFileMappingInput.request_mapping`, nullable), and both the editor and the automap button
in the UI rely on it.

## Export

`export_finished.py` joins the qBittorrent download directory to each file's relative path with
`posixpath.join`, so *_Releasarr and the *arrs must see the same filesystem at the same paths*_.

Episode IDs are resolved from Sonarr, not from Releasarr's database — the mapping's
`(season, episode)` is looked up against `get_episodes(series_id)`:

```python
for series_id, files in files_by_series.items():
    episodes = await self._sonarr.get_episodes(series_id)
    episode_map = {(ep.season_number, ep.episode_number): ep.id for ep in episodes}

    for file in files:
        ...
        episode_id = episode_map.get((file.mapping.season, file.mapping.episode))
```

A mapping pointing at an episode Sonarr does not have is skipped. Movies need no lookup —
Radarr resolves the file against the movie id.

A file is only exportable if its mapping names a request that has a `sonarr_series_id` or
`radarr_movie_id`. `manual_import` returning `False` becomes a `RuntimeError`, which increments
`export_failures_count`; at five, the release drops out of the export queue and needs a manual
re-map or re-grab to get back in.
