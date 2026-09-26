import { useQuery } from '@tanstack/react-query';

import { systemApi } from '@/features/system/api';

export const systemKeys = {
  all: ['system'] as const,
  info: () => [...systemKeys.all, 'info'] as const,
};

/** The running instance's version. It only changes with a deploy, which reloads the app anyway. */
export function useSystemInfo() {
  return useQuery({
    queryKey: systemKeys.info(),
    queryFn: ({ signal }: { signal: AbortSignal }) => systemApi.info(signal),
    staleTime: Infinity,
  });
}
