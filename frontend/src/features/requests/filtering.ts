import type { MediaRequest, MediaRequestStatus } from '@/types';

/**
 * Media type and progress are independent questions — "which series are still
 * downloading?" needs both — so they are separate filters rather than one list
 * of pills where picking a type threw away the status.
 */
export const TYPE_KEYS = ['all', 'movie', 'series'] as const;

export const STATUS_KEYS = [
  'active',
  'all',
  'pending',
  'searching',
  'downloading',
  'completed',
  'failed',
] as const;

export const SORT_KEYS = ['created_desc', 'created_asc', 'title_asc', 'title_desc'] as const;

export type TypeFilter = (typeof TYPE_KEYS)[number];
export type StatusFilter = (typeof STATUS_KEYS)[number];
export type SortKey = (typeof SORT_KEYS)[number];

export const DEFAULT_TYPE: TypeFilter = 'all';

/**
 * Requests still needing attention. A failed request counts: it has not
 * succeeded, and it is the one most likely to need looking at.
 */
export const DEFAULT_STATUS: StatusFilter = 'active';
export const DEFAULT_SORT: SortKey = 'created_desc';

export const isTypeFilter = (value: string | null): value is TypeFilter =>
  Boolean(value) && TYPE_KEYS.includes(value as TypeFilter);

export const isStatusFilter = (value: string | null): value is StatusFilter =>
  Boolean(value) && STATUS_KEYS.includes(value as StatusFilter);

export const isSortKey = (value: string | null): value is SortKey =>
  Boolean(value) && SORT_KEYS.includes(value as SortKey);

const SORTERS: Record<SortKey, (a: MediaRequest, b: MediaRequest) => number> = {
  created_desc: (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  created_asc: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  title_asc: (a, b) => a.title.localeCompare(b.title),
  title_desc: (a, b) => b.title.localeCompare(a.title),
};

const matchesType = (request: MediaRequest, type: TypeFilter): boolean =>
  type === 'all' || request.type === type;

const matchesStatus = (request: MediaRequest, status: StatusFilter): boolean => {
  if (status === 'all') return true;
  if (status === 'active') return request.status !== 'completed';
  return request.status === status;
};

const matchesSearch = (request: MediaRequest, search: string): boolean => {
  if (!search) return true;
  const haystack = [request.title, request.type === 'series' ? request.series_title : undefined];
  return haystack.some((value) => value?.toLowerCase().includes(search));
};

export const filterAndSortRequests = (
  requests: MediaRequest[],
  {
    type,
    status,
    sort,
    search,
  }: { type: TypeFilter; status: StatusFilter; sort: SortKey; search: string },
): MediaRequest[] => {
  const normalizedSearch = search.trim().toLowerCase();

  return requests
    .filter(
      (request) =>
        matchesType(request, type) &&
        matchesStatus(request, status) &&
        matchesSearch(request, normalizedSearch),
    )
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
