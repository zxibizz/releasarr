import { useCallback, useMemo, useState } from 'react';

import type {
  FileRequestMapping,
  MediaRequest,
  ReleaseFile,
  ReleaseFileMappingInput,
  ReleaseFileMappingSuggestion,
  SeriesRequest,
} from '@/types';

export type MappingType = 'movie' | 'series';

/**
 * Flat, editable representation of a file's mapping. The API models this as a
 * discriminated union; the form keeps season/episode optional and only
 * serialises them back for series mappings.
 */
export interface MappingDraft {
  requestId: string;
  requestTitle: string;
  mappingType: MappingType;
  season?: number;
  episode?: number;
}

type DraftMap = Record<string, MappingDraft>;

/** Season number to the request tracking it, for one series. */
type SeasonIndex = Map<number, MediaRequest>;

const EMPTY_DRAFT: MappingDraft = { requestId: '', requestTitle: '', mappingType: 'movie' };
/** Stable defaults so the draft memos don't invalidate on every render. */
const NO_REQUESTS: MediaRequest[] = [];
const NO_SUGGESTIONS: ReleaseFileMappingSuggestion[] = [];

const isSeriesRequest = (request: MediaRequest): request is SeriesRequest =>
  request.type === 'series';

/**
 * Identity of the series a request belongs to. Sonarr's id is authoritative; the
 * series title is the fallback for requests that predate a Sonarr link.
 */
const seriesKeyOf = (sonarrSeriesId: number | null | undefined, seriesTitle: string): string =>
  sonarrSeriesId != null ? `sonarr:${sonarrSeriesId}` : `title:${seriesTitle.trim().toLowerCase()}`;

const seriesKeyOfRequest = (request: SeriesRequest): string =>
  seriesKeyOf(request.sonarr_series_id, request.series_title);

/**
 * A complete-series pack holds several seasons, each tracked by its own request,
 * so files have to be routed per season instead of onto a single request.
 */
const buildSeasonIndexes = (requests: MediaRequest[]): Map<string, SeasonIndex> => {
  const indexes = new Map<string, SeasonIndex>();

  requests.filter(isSeriesRequest).forEach((request) => {
    const key = seriesKeyOfRequest(request);
    const index = indexes.get(key) ?? new Map<number, MediaRequest>();
    if (!index.has(request.season_number)) {
      index.set(request.season_number, request);
    }
    indexes.set(key, index);
  });

  return indexes;
};

const draftFromMapping = (mapping: FileRequestMapping): MappingDraft =>
  mapping.mapping_type === 'series'
    ? {
        requestId: mapping.request_id,
        requestTitle: mapping.request_title ?? '',
        mappingType: 'series',
        season: mapping.season,
        episode: mapping.episode,
      }
    : {
        requestId: mapping.request_id,
        requestTitle: mapping.request_title ?? '',
        mappingType: 'movie',
      };

/** Series draft pointing at whichever request owns `season`, falling back to `fallback`. */
const seriesDraft = (
  season: number | undefined,
  episode: number | undefined,
  fallback: { id: string; title: string },
  seasonIndex: SeasonIndex | undefined,
): MappingDraft => {
  const owner = season !== undefined ? seasonIndex?.get(season) : undefined;

  return {
    requestId: owner?.id ?? fallback.id,
    requestTitle: owner?.title ?? fallback.title,
    mappingType: 'series',
    season,
    episode,
  };
};

/**
 * Only what is already stored. A file the server has not mapped starts blank,
 * so the unsaved-changes count stays honest: anything the form fills in from
 * here on is a proposal nobody has agreed to yet.
 */
const buildInitialDrafts = (files: ReleaseFile[]): DraftMap => {
  const drafts: DraftMap = {};

  files.forEach((file) => {
    drafts[file.id] = file.request_mapping
      ? draftFromMapping(file.request_mapping)
      : { ...EMPTY_DRAFT };
  });

  return drafts;
};

const isSameDraft = (a: MappingDraft, b: MappingDraft): boolean =>
  a.requestId === b.requestId &&
  a.mappingType === b.mappingType &&
  a.season === b.season &&
  a.episode === b.episode;

/**
 * Identity of a batch of proposals by content. Comparing these rather than array
 * references means a caller that rebuilds the list every render still only
 * triggers one pass, instead of looping.
 */
const suggestionsFingerprint = (suggestions: ReleaseFileMappingSuggestion[]): string =>
  suggestions
    .map(({ file_id: fileId, request_mapping: mapping }) =>
      mapping.mapping_type === 'series'
        ? `${fileId}:${mapping.request_id}:${mapping.season}:${mapping.episode}`
        : `${fileId}:${mapping.request_id}`,
    )
    .join('|');

/**
 * Lay the server's proposals over the rows nobody has touched. An edit made
 * while the suggestions were still in flight outranks them.
 */
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

/** A mapping is only persistable once it points at a request. */
const toPayload = (fileId: string, draft: MappingDraft): ReleaseFileMappingInput | null => {
  if (!draft.requestId) {
    return null;
  }

  if (draft.mappingType === 'series') {
    // Guessing 1 here would persist a wrong episode; leave the file unmapped instead.
    if (!draft.season || !draft.episode) {
      return null;
    }

    return {
      file_id: fileId,
      request_mapping: {
        request_id: draft.requestId,
        request_title: draft.requestTitle || undefined,
        mapping_type: 'series',
        season: draft.season,
        episode: draft.episode,
      },
    };
  }

  return {
    file_id: fileId,
    request_mapping: {
      request_id: draft.requestId,
      request_title: draft.requestTitle || undefined,
      mapping_type: 'movie',
    },
  };
};

export function useFileMappingForm(
  files: ReleaseFile[],
  availableRequests: MediaRequest[] = NO_REQUESTS,
  suggestions: ReleaseFileMappingSuggestion[] = NO_SUGGESTIONS,
) {
  const seasonIndexes = useMemo(() => buildSeasonIndexes(availableRequests), [availableRequests]);

  const initialDrafts = useMemo(() => buildInitialDrafts(files), [files]);

  const [drafts, setDrafts] = useState<DraftMap>(() =>
    withSuggestions(initialDrafts, initialDrafts, suggestions),
  );

  // Rebuild drafts whenever the underlying files change (e.g. after a save).
  const [seenInitial, setSeenInitial] = useState(initialDrafts);
  if (seenInitial !== initialDrafts) {
    setSeenInitial(initialDrafts);
    setDrafts(initialDrafts);
  }

  // And fold in each new batch of proposals as it arrives.
  const suggestionsKey = useMemo(() => suggestionsFingerprint(suggestions), [suggestions]);
  const [seenSuggestions, setSeenSuggestions] = useState(suggestionsKey);
  if (seenSuggestions !== suggestionsKey) {
    setSeenSuggestions(suggestionsKey);
    setDrafts((current) => withSuggestions(current, initialDrafts, suggestions));
  }

  const getDraft = useCallback(
    (fileId: string): MappingDraft => drafts[fileId] ?? EMPTY_DRAFT,
    [drafts],
  );

  const updateDraft = useCallback((fileId: string, changes: Partial<MappingDraft>) => {
    setDrafts((current) => ({
      ...current,
      [fileId]: { ...(current[fileId] ?? EMPTY_DRAFT), ...changes },
    }));
  }, []);

  const selectRequest = useCallback(
    (fileId: string, request: MediaRequest | null) => {
      if (!request) {
        updateDraft(fileId, { ...EMPTY_DRAFT });
        return;
      }

      if (isSeriesRequest(request)) {
        const existing = drafts[fileId];
        updateDraft(fileId, {
          requestId: request.id,
          requestTitle: request.title,
          mappingType: 'series',
          season: existing?.season ?? request.season_number,
          episode: existing?.episode,
        });
      } else {
        updateDraft(fileId, {
          requestId: request.id,
          requestTitle: request.title,
          mappingType: 'movie',
          season: undefined,
          episode: undefined,
        });
      }
    },
    [drafts, updateDraft],
  );

  /**
   * Applies one request to every listed file. For a series the request only sets
   * the series: each file still lands on the request owning its own season.
   */
  const applyToAll = useCallback(
    (request: MediaRequest, targetFiles: ReleaseFile[]) => {
      const seasonIndex = isSeriesRequest(request)
        ? seasonIndexes.get(seriesKeyOfRequest(request))
        : undefined;

      setDrafts((current) => {
        const next = { ...current };

        targetFiles.forEach((file) => {
          if (!isSeriesRequest(request)) {
            next[file.id] = {
              requestId: request.id,
              requestTitle: request.title,
              mappingType: 'movie',
            };
            return;
          }

          const draft = current[file.id];
          next[file.id] = seriesDraft(
            draft?.season ?? request.season_number,
            draft?.episode,
            request,
            seasonIndex,
          );
        });

        return next;
      });
    },
    [seasonIndexes],
  );

  /**
   * Everything the automapper proposes, and nothing else: the stored mappings go
   * first, so a file it proposes nothing for ends up unmapped rather than keeping
   * whatever was chosen for it last time.
   */
  const automap = useCallback(() => {
    const next: DraftMap = {};

    files.forEach((file) => {
      next[file.id] = { ...EMPTY_DRAFT };
    });

    suggestions.forEach((suggestion) => {
      next[suggestion.file_id] = draftFromMapping(suggestion.request_mapping);
    });

    setDrafts(next);
  }, [files, suggestions]);

  const reset = useCallback(() => setDrafts(initialDrafts), [initialDrafts]);

  const isDirty = useCallback(
    (fileId: string) => !isSameDraft(getDraft(fileId), initialDrafts[fileId] ?? EMPTY_DRAFT),
    [getDraft, initialDrafts],
  );

  const dirtyFileIds = useMemo(
    () =>
      Object.keys(drafts).filter(
        (fileId) => !isSameDraft(drafts[fileId], initialDrafts[fileId] ?? EMPTY_DRAFT),
      ),
    [drafts, initialDrafts],
  );

  const buildPayload = useCallback(
    (targetFiles: ReleaseFile[]): ReleaseFileMappingInput[] =>
      targetFiles
        .map((file) => toPayload(file.id, getDraft(file.id)))
        .filter((entry): entry is ReleaseFileMappingInput => entry !== null),
    [getDraft],
  );

  return {
    getDraft,
    updateDraft,
    selectRequest,
    applyToAll,
    automap,
    reset,
    isDirty,
    dirtyFileIds,
    buildPayload,
  };
}
