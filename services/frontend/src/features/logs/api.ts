import { apiRequest } from '@/lib/api/client';
import type { LogService, LogsResponse, RequestLogLevel, SyncJobKind } from '@/types';

/** Upper bound on entries pulled per request; the backend paginates at 20 by default. */
const LOGS_PER_PAGE = 100;

interface ListLogsParams {
  page?: number;
  perPage?: number;
  /** Restricts results to entries logged while this background task ran. */
  task?: SyncJobKind;
  /** Restricts results to entries written by this process. */
  service?: LogService;
  /** Least severity to return, along with everything worse. */
  minLevel?: RequestLogLevel;
}

export const logsApi = {
  byRequest: (requestId: string, signal?: AbortSignal) =>
    apiRequest<LogsResponse>('/logs', {
      signal,
      query: { request_id: requestId, per_page: LOGS_PER_PAGE },
    }),

  list: (
    { page = 1, perPage = 25, task, service, minLevel }: ListLogsParams = {},
    signal?: AbortSignal,
  ) =>
    apiRequest<LogsResponse>('/logs', {
      signal,
      query: {
        page,
        per_page: perPage,
        ...(task ? { task } : {}),
        ...(service ? { service } : {}),
        ...(minLevel ? { min_level: minLevel } : {}),
      },
    }),
};
