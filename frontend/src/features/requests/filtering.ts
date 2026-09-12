import type { MediaRequest, MediaRequestStatus } from '@/types';

export const FILTER_KEYS = [
  'all',
  'movies',
  'series',
  'pending',
  'searching',
  'downloading',
  'completed',
  'failed',
] as const;

export const SORT_KEYS = ['created_desc', 'created_asc', 'title_asc', 'title_desc'] as const;

export type FilterKey = (typeof FILTER_KEYS)[number];
export type SortKey = (typeof SORT_KEYS)[number];

export const DEFAULT_FILTER: FilterKey = 'all';
export const DEFAULT_SORT: SortKey = 'created_desc';

export const isFilterKey = (value: string | null): value is FilterKey =>
  Boolean(value) && FILTER_KEYS.includes(value as FilterKey);

export const isSortKey = (value: string | null): value is SortKey =>
  Boolean(value) && SORT_KEYS.includes(value as SortKey);

const SORTERS: Record<SortKey, (a: MediaRequest, b: MediaRequest) => number> = {
  created_desc: (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  created_asc: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  title_asc: (a, b) => a.title.localeCompare(b.title),
  title_desc: (a, b) => b.title.localeCompare(a.title),
};

const matchesFilter = (request: MediaRequest, filter: FilterKey): boolean => {
  if (filter === 'all') return true;
  if (filter === 'movies') return request.type === 'movie';
  if (filter === 'series') return request.type === 'series';
  return request.status === filter;
};

const matchesSearch = (request: MediaRequest, search: string): boolean => {
  if (!search) return true;
  const haystack = [request.title, request.type === 'series' ? request.series_title : undefined];
  return haystack.some((value) => value?.toLowerCase().includes(search));
};

export const filterAndSortRequests = (
  requests: MediaRequest[],
  { filter, sort, search }: { filter: FilterKey; sort: SortKey; search: string },
): MediaRequest[] => {
  const normalizedSearch = search.trim().toLowerCase();

  return requests
    .filter((request) => matchesFilter(request, filter) && matchesSearch(request, normalizedSearch))
    .sort(SORTERS[sort]);
};

export interface RequestStats {
  total: number;
  byType: Partial<Record<MediaRequest['type'], number>>;
  byStatus: Partial<Record<MediaRequestStatus, number>>;
}

export const buildStats = (requests: MediaRequest[]): RequestStats =>
  requests.reduce<RequestStats>(
    (stats, request) => {
      stats.total += 1;
      stats.byType[request.type] = (stats.byType[request.type] ?? 0) + 1;
      stats.byStatus[request.status] = (stats.byStatus[request.status] ?? 0) + 1;
      return stats;
    },
    { total: 0, byType: {}, byStatus: {} },
  );
