import { useSearchParams } from 'react-router-dom';

import {
  DEFAULT_SORT,
  DEFAULT_STATUS,
  DEFAULT_TYPE,
  isSortKey,
  isStatusFilter,
  isTypeFilter,
  type SortKey,
  type StatusFilter,
  type TypeFilter,
} from '@/features/requests/filtering';

/** Keeps list filter/sort/search state in the URL so views are shareable. */
export function useRequestFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const typeParam = searchParams.get('type');
  const statusParam = searchParams.get('status');
  const sortParam = searchParams.get('sort');

  const type: TypeFilter = isTypeFilter(typeParam) ? typeParam : DEFAULT_TYPE;
  const status: StatusFilter = isStatusFilter(statusParam) ? statusParam : DEFAULT_STATUS;
  const sort: SortKey = isSortKey(sortParam) ? sortParam : DEFAULT_SORT;
  const search = searchParams.get('q') ?? '';

  const update = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (!value) {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    setSearchParams(next, { replace: true });
  };

  return {
    type,
    status,
    sort,
    search,
    setType: (value: TypeFilter) => update('type', value === DEFAULT_TYPE ? null : value),
    setStatus: (value: StatusFilter) => update('status', value === DEFAULT_STATUS ? null : value),
    setSort: (value: SortKey) => update('sort', value === DEFAULT_SORT ? null : value),
    setSearch: (value: string) => update('q', value.trim() ? value : null),
  };
}
