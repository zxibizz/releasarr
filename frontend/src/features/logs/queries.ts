import { useQuery } from '@tanstack/react-query';

import { logsApi } from '@/features/logs/api';
import type { SyncJobKind } from '@/types';

export const LOGS_PAGE_SIZE = 25;

export const logKeys = {
  all: ['logs'] as const,
  byRequest: (requestId: string) => [...logKeys.all, 'by-request', requestId] as const,
  list: (filters: { page: number; task?: SyncJobKind }) =>
    [...logKeys.all, 'list', filters] as const,
};

/**
 * Activity log for a single request. Only fetched while the modal is open, since
 * the backend parses the whole log file on every call.
 */
export function useRequestLogs(requestId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: logKeys.byRequest(requestId ?? ''),
    queryFn: ({ signal }: { signal: AbortSignal }) => logsApi.byRequest(requestId ?? '', signal),
    enabled: Boolean(requestId) && enabled,
  });
}

/**
 * A page of application logs, optionally narrowed to one background task.
 *
 * The previous page stays on screen while the next one loads, so paging and
 * changing the filter do not blank the table.
 */
export function useLogs({ page, task }: { page: number; task?: SyncJobKind }) {
  return useQuery({
    queryKey: logKeys.list({ page, task }),
    queryFn: ({ signal }) => logsApi.list({ page, perPage: LOGS_PAGE_SIZE, task }, signal),
    placeholderData: (previous) => previous,
  });
}
