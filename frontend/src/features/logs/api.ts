import { apiRequest } from '@/lib/api/client';
import type { LogsResponse } from '@/types';

/** Upper bound on entries pulled per request; the backend paginates at 20 by default. */
const LOGS_PER_PAGE = 100;

export const logsApi = {
  byRequest: (requestId: string, signal?: AbortSignal) =>
    apiRequest<LogsResponse>('/logs', {
      signal,
      query: { request_id: requestId, per_page: LOGS_PER_PAGE },
    }),
};
