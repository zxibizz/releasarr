import { useQuery } from '@tanstack/react-query';

import { requestsApi, type RequestListFilters } from '@/features/requests/api';

const serializeFilters = (filters?: RequestListFilters) =>
  Object.entries(filters ?? {})
    .filter(([, value]) => value !== undefined && value !== null)
    .sort(([a], [b]) => a.localeCompare(b));

export const requestKeys = {
  all: ['requests'] as const,
  lists: () => [...requestKeys.all, 'list'] as const,
  list: (filters?: RequestListFilters) => {
    const serialized = serializeFilters(filters);
    return serialized.length === 0
      ? requestKeys.lists()
      : ([...requestKeys.lists(), serialized] as const);
  },
  detail: (id: string) => [...requestKeys.all, 'detail', id] as const,
};

export const requestsListQuery = (filters?: RequestListFilters) => ({
  queryKey: requestKeys.list(filters),
  queryFn: ({ signal }: { signal: AbortSignal }) => requestsApi.list(filters, signal),
});

export const requestDetailQuery = (id: string) => ({
  queryKey: requestKeys.detail(id),
  queryFn: ({ signal }: { signal: AbortSignal }) => requestsApi.detail(id, signal),
});

export function useRequestsList(filters?: RequestListFilters) {
  const query = useQuery(requestsListQuery(filters));

  return {
    ...query,
    requests: query.data?.requests ?? [],
    total: query.data?.total ?? 0,
  };
}

export function useRequest(id: string | undefined) {
  return useQuery({
    ...requestDetailQuery(id ?? ''),
    enabled: Boolean(id),
  });
}
