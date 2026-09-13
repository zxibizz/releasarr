import { apiRequest } from '@/lib/api/client';
import type {
  MediaRequest,
  MediaRequestStatus,
  MediaType,
  RequestsResponse,
  SeasonEpisodesResponse,
  SeriesSeasonsResponse,
  UpdateSeasonsPayload,
} from '@/types';

export interface RequestListFilters {
  page?: number;
  perPage?: number;
  status?: MediaRequestStatus;
  type?: MediaType;
}

export const requestsApi = {
  list: (filters: RequestListFilters = {}, signal?: AbortSignal) =>
    apiRequest<RequestsResponse>('/requests', {
      signal,
      query: {
        page: filters.page,
        per_page: filters.perPage,
        status: filters.status,
        type: filters.type,
      },
    }),

  detail: (id: string, signal?: AbortSignal) =>
    apiRequest<MediaRequest>(`/requests/${encodeURIComponent(id)}`, { signal }),

  remove: (id: string) =>
    apiRequest<void>(`/requests/${encodeURIComponent(id)}`, { method: 'DELETE' }),

  episodes: (id: string, signal?: AbortSignal) =>
    apiRequest<SeasonEpisodesResponse>(`/requests/${encodeURIComponent(id)}/episodes`, { signal }),

  seasons: (id: string, signal?: AbortSignal) =>
    apiRequest<SeriesSeasonsResponse>(`/requests/${encodeURIComponent(id)}/seasons`, { signal }),

  updateSeasons: (id: string, payload: UpdateSeasonsPayload) =>
    apiRequest<SeriesSeasonsResponse>(`/requests/${encodeURIComponent(id)}/seasons`, {
      method: 'PUT',
      body: payload,
    }),
};
