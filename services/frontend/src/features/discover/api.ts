import { apiRequest } from '@/lib/api/client';
import type {
  AddRequestPayload,
  AddRequestResponse,
  MediaSearchResponse,
  MediaType,
  RootFoldersResponse,
  SeriesSeasonsResponse,
} from '@/types';

export const discoverApi = {
  /** Searches movies and series together; the endpoint's type filter is unused. */
  search: (query: string, language?: string, signal?: AbortSignal) =>
    apiRequest<MediaSearchResponse>('/discover/search', {
      signal,
      query: { q: query, lang: language },
    }),

  seriesSeasons: (tvdbId: number, signal?: AbortSignal) =>
    apiRequest<SeriesSeasonsResponse>(`/discover/series/${tvdbId}/seasons`, { signal }),

  rootFolders: (type: MediaType, signal?: AbortSignal) =>
    apiRequest<RootFoldersResponse>('/discover/root-folders', { signal, query: { type } }),

  addRequest: (payload: AddRequestPayload) =>
    apiRequest<AddRequestResponse>('/discover/requests', { method: 'POST', body: payload }),
};
