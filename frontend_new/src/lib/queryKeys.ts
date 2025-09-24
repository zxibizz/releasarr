import type { MediaRequest, Release } from '@/types';

export type RequestListFilters = {
  page?: number;
  perPage?: number;
  status?: MediaRequest['status'];
  type?: MediaRequest['type'];
};

export type ReleaseListFilters = {
  status?: Release['status'];
  requestId?: string;
};

const withListFilters = <T extends object>(scope: string, filters?: T) => {
  if (!filters) {
    return [scope, 'list'] as const;
  }

  const serialized = Object.entries(filters)
    .filter(([, value]) => value !== undefined && value !== null)
    .sort(([a], [b]) => a.localeCompare(b));

  return [scope, 'list', serialized] as const;
};

export const requestsKeys = {
  all: ['requests'] as const,
  list: (filters?: RequestListFilters) => withListFilters('requests', filters),
  detail: (id: string) => ['requests', 'detail', id] as const,
};

export const releasesKeys = {
  all: ['releases'] as const,
  list: (filters?: ReleaseListFilters) => withListFilters('releases', filters),
  detail: (id: string) => ['releases', 'detail', id] as const,
  byRequest: (requestId: string) => ['releases', 'by-request', requestId] as const,
};
