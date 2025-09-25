import type { Release } from '@/types';

export type ReleaseListFilters = {
  status?: Release['status'];
  requestId?: string;
};

const scope = 'releases' as const;

const serializeFilters = <T extends object>(filters: T | undefined) =>
  Object.entries(filters ?? {})
    .filter(([, value]) => value !== undefined && value !== null)
    .sort(([a], [b]) => a.localeCompare(b));

const listKey = (filters?: ReleaseListFilters) => {
  const serialized = serializeFilters(filters);
  if (serialized.length === 0) {
    return [scope, 'list'] as const;
  }
  return [scope, 'list', serialized] as const;
};

export const releasesKeys = {
  all: [scope] as const,
  list: listKey,
  detail: (id: string) => [scope, 'detail', id] as const,
  byRequest: (requestId: string) => [scope, 'by-request', requestId] as const,
} as const;

export type ReleasesListQueryKey = ReturnType<typeof releasesKeys.list>;
export type ReleasesByRequestQueryKey = ReturnType<typeof releasesKeys.byRequest>;
export type ReleaseDetailQueryKey = ReturnType<typeof releasesKeys.detail>;
