import { QueryClient } from '@tanstack/react-query';

import { ApiError } from '@/lib/api/client';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Client errors will not succeed on retry.
        if (error instanceof ApiError && error.status && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});
