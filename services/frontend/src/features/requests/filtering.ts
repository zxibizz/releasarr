/**
 * Media type and progress are independent questions — "which series are still
 * downloading?" needs both — so they are separate filters rather than one list
 * of pills where picking a type threw away the status.
 *
 * The keys below are the vocabulary the list page, the URL and the API share;
 * the filtering itself happens server-side.
 */
export const TYPE_KEYS = ['all', 'movie', 'series'] as const;

export const STATUS_KEYS = [
  'active',
  'all',
  'pending',
  'searching',
  'downloading',
  'monitoring',
  'importing',
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
