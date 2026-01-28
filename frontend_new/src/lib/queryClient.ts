import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry(failureCount, error) {
        // Avoid retrying on 4xx errors while preserving default behaviour for network issues.
        const status =
          typeof (error as { status?: number } | undefined)?.status === 'number'
            ? (error as { status?: number }).status
            : undefined;
        if (status && status >= 400 && status < 500) {
          return false;
        }
        return failureCount < 3;
      },
    },
    mutations: {
      retry: 0,
    },
  },
});
