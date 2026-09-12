import { useSearchParams } from 'react-router-dom';

import {
  DEFAULT_FILTER,
  DEFAULT_SORT,
  isFilterKey,
  isSortKey,
  type FilterKey,
  type SortKey,
} from '@/features/requests/filtering';

/** Keeps list filter/sort/search state in the URL so views are shareable. */
export function useRequestFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filterParam = searchParams.get('filter');
  const sortParam = searchParams.get('sort');

  const filter: FilterKey = isFilterKey(filterParam) ? filterParam : DEFAULT_FILTER;
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
    filter,
    sort,
    search,
    setFilter: (value: FilterKey) => update('filter', value === DEFAULT_FILTER ? null : value),
    setSort: (value: SortKey) => update('sort', value === DEFAULT_SORT ? null : value),
    setSearch: (value: string) => update('q', value.trim() ? value : null),
  };
}
