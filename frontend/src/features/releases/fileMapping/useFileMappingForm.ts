import { useCallback, useMemo, useState } from 'react';

import type {
  FileRequestMapping,
  MediaRequest,
  ReleaseFile,
  ReleaseFileMappingInput,
  SeriesRequest,
} from '@/types';
import { compareByFileName, parseEpisodeFromFile } from '@/utils/files';

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

export interface DefaultRequest {
  id: string;
  title: string;
  type: MappingType;
  seasonNumber?: number;
  seriesTitle?: string;
  sonarrSeriesId?: number | null;
}

type DraftMap = Record<string, MappingDraft>;

/** Season number to the request tracking it, for one series. */
type SeasonIndex = Map<number, MediaRequest>;

const EMPTY_DRAFT: MappingDraft = { requestId: '', requestTitle: '', mappingType: 'movie' };
/** Stable default so the draft memos don't invalidate on every render. */
const NO_REQUESTS: MediaRequest[] = [];

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

const seriesKeyOfDefault = (defaultRequest: DefaultRequest): string | undefined =>
  defaultRequest.type === 'series'
    ? seriesKeyOf(defaultRequest.sonarrSeriesId, defaultRequest.seriesTitle ?? defaultRequest.title)
    : undefined;

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

const buildInitialDrafts = (
  files: ReleaseFile[],
  defaultRequest: DefaultRequest | undefined,
  seasonIndexes: Map<string, SeasonIndex>,
): DraftMap => {
  const drafts: DraftMap = {};
  const seriesKey = defaultRequest ? seriesKeyOfDefault(defaultRequest) : undefined;
  const seasonIndex = seriesKey ? seasonIndexes.get(seriesKey) : undefined;

  files.forEach((file) => {
    if (file.request_mapping) {
      drafts[file.id] = draftFromMapping(file.request_mapping);
      return;
    }

    if (!defaultRequest) {
      drafts[file.id] = { ...EMPTY_DRAFT };
      return;
    }

    if (defaultRequest.type === 'series') {
      const parsed = parseEpisodeFromFile(file);
      drafts[file.id] = seriesDraft(
        parsed.season ?? defaultRequest.seasonNumber,
        parsed.episode,
        defaultRequest,
        seasonIndex,
      );
    } else {
      drafts[file.id] = {
        requestId: defaultRequest.id,
        requestTitle: defaultRequest.title,
        mappingType: 'movie',
      };
    }
  });

  return drafts;
};

const isSameDraft = (a: MappingDraft, b: MappingDraft): boolean =>
  a.requestId === b.requestId &&
  a.mappingType === b.mappingType &&
  a.season === b.season &&
  a.episode === b.episode;

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
  defaultRequest?: DefaultRequest,
  availableRequests: MediaRequest[] = NO_REQUESTS,
) {
  const seasonIndexes = useMemo(() => buildSeasonIndexes(availableRequests), [availableRequests]);
  const requestsById = useMemo(
    () => new Map(availableRequests.map((request) => [request.id, request])),
    [availableRequests],
  );

  const initialDrafts = useMemo(
    () => buildInitialDrafts(files, defaultRequest, seasonIndexes),
    [files, defaultRequest, seasonIndexes],
  );

  const [drafts, setDrafts] = useState<DraftMap>(initialDrafts);
  const [resetToken, setResetToken] = useState(0);

  // Rebuild drafts whenever the underlying files change (e.g. after a save).
  const [seenInitial, setSeenInitial] = useState(initialDrafts);
  if (seenInitial !== initialDrafts) {
    setSeenInitial(initialDrafts);
    setDrafts(initialDrafts);
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
    (fileId: string, request: MediaRequest | null, file: ReleaseFile) => {
      if (!request) {
        updateDraft(fileId, { ...EMPTY_DRAFT });
        return;
      }

      if (isSeriesRequest(request)) {
        const parsed = parseEpisodeFromFile(file);
        const existing = drafts[fileId];
        updateDraft(fileId, {
          requestId: request.id,
          requestTitle: request.title,
          mappingType: 'series',
          season: existing?.season ?? parsed.season ?? request.season_number,
          episode: existing?.episode ?? parsed.episode,
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

          const parsed = parseEpisodeFromFile(file);
          next[file.id] = seriesDraft(
            parsed.season ?? request.season_number,
            parsed.episode ?? current[file.id]?.episode,
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
   * Fills season/episode for series mappings, preferring numbers parsed from the
   * file and falling back to a counter kept per season.
   */
  const autoFillEpisodes = useCallback(
    (targetFiles: ReleaseFile[]) => {
      setDrafts((current) => {
        const next = { ...current };
        const lastEpisode = new Map<number, number>();

        [...targetFiles].sort(compareByFileName).forEach((file) => {
          const draft = next[file.id];
          if (!draft?.requestId || draft.mappingType !== 'series') {
            return;
          }

          const parsed = parseEpisodeFromFile(file);
          const season = parsed.season ?? draft.season;
          if (season === undefined) {
            return;
          }

          const episode = parsed.episode ?? (lastEpisode.get(season) ?? 0) + 1;
          lastEpisode.set(season, Math.max(lastEpisode.get(season) ?? 0, episode));

          const request = requestsById.get(draft.requestId);
          const seasonIndex =
            request && isSeriesRequest(request)
              ? seasonIndexes.get(seriesKeyOfRequest(request))
              : undefined;

          next[file.id] = seriesDraft(
            season,
            episode,
            { id: draft.requestId, title: draft.requestTitle },
            seasonIndex,
          );
        });

        return next;
      });
    },
    [requestsById, seasonIndexes],
  );

  const reset = useCallback(() => {
    setDrafts(initialDrafts);
    setResetToken((token) => token + 1);
  }, [initialDrafts]);

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

  const canAutoFill = useMemo(
    () =>
      Object.values(drafts).some(
        (draft) => draft.mappingType === 'series' && Boolean(draft.requestId),
      ),
    [drafts],
  );

  return {
    getDraft,
    updateDraft,
    selectRequest,
    applyToAll,
    autoFillEpisodes,
    reset,
    resetToken,
    isDirty,
    dirtyFileIds,
    buildPayload,
    canAutoFill,
  };
}
