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

/**
 * Runs a route loader's prefetch, unless the browser reports no connection.
 *
 * React Query *pauses* a query rather than failing it while it believes there is
 * no connection, and a paused query may never settle. A loader that waited on
 * one would leave the router in its initial loading state — showing the
 * hydration fallback for good instead of the offline screen that the gate below
 * the loaders would otherwise render. Nothing is worth prefetching with no
 * connection anyway, so the loader steps aside and lets that screen answer.
 *
 * This reads `navigator.onLine` rather than React Query's online manager on
 * purpose: the manager only learns the state from a browser event, so on a cold
 * start it can still report online while the browser is not.
 */
export async function prefetchWhenOnline(load: () => Promise<unknown>): Promise<void> {
  if (!navigator.onLine) {
    return;
  }
  await load();
}
