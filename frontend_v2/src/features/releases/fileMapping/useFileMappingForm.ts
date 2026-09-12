import { useCallback, useMemo, useState } from 'react';

import type { FileRequestMapping, MediaRequest, ReleaseFile, ReleaseFileMappingInput } from '@/types';
import { parseEpisodeFromFilename } from '@/utils/files';

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
}

type DraftMap = Record<string, MappingDraft>;

const EMPTY_DRAFT: MappingDraft = { requestId: '', requestTitle: '', mappingType: 'movie' };

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

const buildInitialDrafts = (files: ReleaseFile[], defaultRequest?: DefaultRequest): DraftMap => {
  const drafts: DraftMap = {};

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
      const parsed = parseEpisodeFromFilename(file.name);
      drafts[file.id] = {
        requestId: defaultRequest.id,
        requestTitle: defaultRequest.title,
        mappingType: 'series',
        season: parsed.season ?? defaultRequest.seasonNumber ?? 1,
        episode: parsed.episode ?? 1,
      };
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
    return {
      file_id: fileId,
      request_mapping: {
        request_id: draft.requestId,
        request_title: draft.requestTitle || undefined,
        mapping_type: 'series',
        season: draft.season && draft.season > 0 ? draft.season : 1,
        episode: draft.episode && draft.episode > 0 ? draft.episode : 1,
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

export function useFileMappingForm(files: ReleaseFile[], defaultRequest?: DefaultRequest) {
  const initialDrafts = useMemo(
    () => buildInitialDrafts(files, defaultRequest),
    [files, defaultRequest],
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
    (fileId: string, request: MediaRequest | null, fileName: string) => {
      if (!request) {
        updateDraft(fileId, { ...EMPTY_DRAFT });
        return;
      }

      if (request.type === 'series') {
        const parsed = parseEpisodeFromFilename(fileName);
        const existing = drafts[fileId];
        updateDraft(fileId, {
          requestId: request.id,
          requestTitle: request.title,
          mappingType: 'series',
          season: existing?.season ?? parsed.season ?? request.season_number ?? 1,
          episode: existing?.episode ?? parsed.episode ?? 1,
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

  /** Applies one request to every listed file at once. */
  const applyToAll = useCallback(
    (request: MediaRequest, targetFiles: ReleaseFile[]) => {
      setDrafts((current) => {
        const next = { ...current };
        targetFiles.forEach((file) => {
          if (request.type === 'series') {
            const parsed = parseEpisodeFromFilename(file.name);
            next[file.id] = {
              requestId: request.id,
              requestTitle: request.title,
              mappingType: 'series',
              season: parsed.season ?? request.season_number ?? 1,
              episode: parsed.episode ?? current[file.id]?.episode ?? 1,
            };
          } else {
            next[file.id] = {
              requestId: request.id,
              requestTitle: request.title,
              mappingType: 'movie',
            };
          }
        });
        return next;
      });
    },
    [],
  );

  /**
   * Fills season/episode for series mappings, preferring numbers parsed from
   * the filename and falling back to a sequential counter.
   */
  const autoFillEpisodes = useCallback(
    (targetFiles: ReleaseFile[]) => {
      setDrafts((current) => {
        const next = { ...current };
        let sequential = 1;

        [...targetFiles]
          .sort((a, b) => a.name.localeCompare(b.name))
          .forEach((file) => {
            const draft = next[file.id];
            if (!draft?.requestId || draft.mappingType !== 'series') {
              return;
            }

            const parsed = parseEpisodeFromFilename(file.name);
            const episode = parsed.episode ?? sequential;
            sequential = Math.max(sequential, episode + 1);

            next[file.id] = {
              ...draft,
              season: parsed.season ?? draft.season ?? 1,
              episode,
            };
          });

        return next;
      });
    },
    [],
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
    () => Object.keys(drafts).filter((fileId) => !isSameDraft(drafts[fileId], initialDrafts[fileId] ?? EMPTY_DRAFT)),
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
