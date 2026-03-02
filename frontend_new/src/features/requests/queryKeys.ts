import type { MediaRequest } from '@/types';

export type RequestListFilters = {
  page?: number;
  perPage?: number;
  status?: MediaRequest['status'];
  type?: MediaRequest['type'];
};

const scope = 'requests' as const;

const serializeFilters = <T extends object>(filters: T | undefined) =>
  Object.entries(filters ?? {})
    .filter(([, value]) => value !== undefined && value !== null)
    .sort(([a], [b]) => a.localeCompare(b));

const listKey = (filters?: RequestListFilters) => {
  const serialized = serializeFilters(filters);
  if (serialized.length === 0) {
    return [scope, 'list'] as const;
  }
  return [scope, 'list', serialized] as const;
};

export const requestsKeys = {
  all: [scope] as const,
  list: listKey,
  detail: (id: string) => [scope, 'detail', id] as const,
} as const;

export type RequestsListQueryKey = ReturnType<typeof requestsKeys.list>;
export type RequestDetailQueryKey = ReturnType<typeof requestsKeys.detail>;
