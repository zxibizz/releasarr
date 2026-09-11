import { apiRequest } from '@/lib/api/client';
import type { MediaRequest, MediaRequestStatus, MediaType, RequestsResponse } from '@/types';

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
};
