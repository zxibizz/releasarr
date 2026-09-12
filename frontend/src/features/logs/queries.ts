import { useQuery } from '@tanstack/react-query';

import { logsApi } from '@/features/logs/api';

export const logKeys = {
  all: ['logs'] as const,
  byRequest: (requestId: string) => [...logKeys.all, 'by-request', requestId] as const,
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
