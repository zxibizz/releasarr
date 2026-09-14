import { notifications } from '@mantine/notifications';
import { useMutation } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { releasesApi } from '@/features/releases/api';
import type { ReleaseSearchResult } from '@/types';
import { getErrorMessage } from '@/utils/errors';

export type SortField = 'age' | 'seeders' | 'leechers' | 'size';
export type SortOrder = 'desc' | 'asc';

export const SORT_FIELDS: SortField[] = ['age', 'seeders', 'leechers', 'size'];
export const DEFAULT_SORT_FIELD: SortField = 'age';
export const DEFAULT_SOURCE_FILTER = 'all';
export const SEARCH_TAB = 'search';
export const MANUAL_TAB = 'manual';

export const NATURAL_SORT_ORDER: Record<SortField, SortOrder> = {
  age: 'asc',
  seeders: 'desc',
  leechers: 'desc',
  size: 'desc',
};

const DAY_IN_MS = 86_400_000;
const SIZE_MULTIPLIERS: Record<string, number> = {
  B: 1,
  KB: 1024,
  MB: 1024 ** 2,
  GB: 1024 ** 3,
  TB: 1024 ** 4,
  PB: 1024 ** 5,
};

const parseSizeToBytes = (size: string | null | undefined): number | null => {
  const match = size?.trim().match(/^([\d.]+)\s*([KMGTP]?B)$/i);
  if (!match) return null;
  const value = Number.parseFloat(match[1]);
  const multiplier = SIZE_MULTIPLIERS[match[2].toUpperCase()];
  return Number.isNaN(value) || !multiplier ? null : value * multiplier;
};

export const ageInDays = (candidate: ReleaseSearchResult): number | null => {
  if (!candidate.publish_date) return null;
  const published = new Date(candidate.publish_date).getTime();
  if (Number.isNaN(published)) return null;
  return Math.max(0, (Date.now() - published) / DAY_IN_MS);
};

const sortValue = (candidate: ReleaseSearchResult, field: SortField): number | null => {
  if (field === 'age') return ageInDays(candidate);
  if (field === 'seeders') return candidate.seeders ?? null;
  if (field === 'leechers') return candidate.leechers ?? null;
  return parseSizeToBytes(candidate.size);
};

interface UseReleaseSearchOptions {
  requestId: string;
  prefillQuery?: string;
  seasonNumber?: number;
  focusToken: number;
  onDownloadQueued: () => void;
}

export function useReleaseSearch({
  requestId,
  prefillQuery,
  seasonNumber,
  focusToken,
  onDownloadQueued,
}: UseReleaseSearchOptions) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const [activeTab, setActiveTab] = useState<string>(SEARCH_TAB);
  const [query, setQuery] = useState(prefillQuery ?? '');
  const [results, setResults] = useState<ReleaseSearchResult[]>([]);
  const [searchedQuery, setSearchedQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>(DEFAULT_SORT_FIELD);
  const [sortOrder, setSortOrder] = useState<SortOrder>(NATURAL_SORT_ORDER[DEFAULT_SORT_FIELD]);
  const [sourceFilter, setSourceFilter] = useState(DEFAULT_SOURCE_FILTER);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  const normalizedQuery = query.replace(/\s+/g, ' ').trim();
  const seasonToken = seasonNumber === undefined ? null : String(seasonNumber);
  const seasonInQuery = Boolean(
    seasonToken && new RegExp(`(^|\\s)${seasonToken}(\\s|$)`, 'i').test(normalizedQuery),
  );

  const search = useMutation({
    mutationFn: (value: string) => releasesApi.search(value, requestId),
    onSuccess: (response, value) => {
      setResults(response.results ?? []);
      setSearchedQuery(value);
    },
    onError: (error) => {
      notifications.show({
        title: t('releaseSearch.toasts.searchFailedTitle'),
        message: getErrorMessage(error, t('releaseSearch.toasts.searchFailedFallback')),
        color: 'red',
      });
    },
  });

  const download = useMutation({
    mutationFn: (candidate: ReleaseSearchResult) =>
      releasesApi.queueDownload(requestId, { release_id: candidate.release_id }),
    onSuccess: (response, candidate) => {
      notifications.show({
        title: t('releaseSearch.toasts.downloadQueuedTitle'),
        message:
          response?.message ??
          t('releaseSearch.toasts.downloadQueuedFallback', { name: candidate.release_name }),
        color: 'teal',
      });
      setResults([]);
      setSearchedQuery('');
      setQuery('');
      onDownloadQueued();
    },
    onError: (error) => {
      notifications.show({
        title: t('releaseSearch.toasts.downloadFailedTitle'),
        message: getErrorMessage(error, t('releaseSearch.toasts.downloadFailedFallback')),
        color: 'red',
      });
    },
    onSettled: () => setDownloadingId(null),
  });

  const [lastPrefill, setLastPrefill] = useState(prefillQuery);
  if (prefillQuery !== lastPrefill) {
    setLastPrefill(prefillQuery);
    setQuery(prefillQuery ?? '');
  }

  const [lastFocusToken, setLastFocusToken] = useState(focusToken);
  if (focusToken !== lastFocusToken) {
    setLastFocusToken(focusToken);
    if (focusToken > 0) setActiveTab(SEARCH_TAB);
  }

  useEffect(() => {
    if (focusToken > 0) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [focusToken]);

  const sources = useMemo(
    () => [...new Set(results.map((result) => result.source).filter(Boolean))].sort() as string[],
    [results],
  );

  const visibleResults = useMemo(() => {
    const filtered =
      sourceFilter === DEFAULT_SOURCE_FILTER
        ? results
        : results.filter((result) => result.source === sourceFilter);

    return [...filtered].sort((a, b) => {
      const aValue = sortValue(a, sortField);
      const bValue = sortValue(b, sortField);
      if (aValue == null && bValue == null) return a.release_name.localeCompare(b.release_name);
      if (aValue == null) return 1;
      if (bValue == null) return -1;
      const diff = sortOrder === 'desc' ? bValue - aValue : aValue - bValue;
      return diff !== 0 ? diff : a.release_name.localeCompare(b.release_name);
    });
  }, [results, sourceFilter, sortField, sortOrder]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (normalizedQuery) search.mutate(normalizedQuery);
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setSearchedQuery('');
    setSourceFilter(DEFAULT_SOURCE_FILTER);
  };

  return {
    activeTab,
    setActiveTab,
    query,
    setQuery,
    results,
    searchedQuery,
    sortField,
    setSortField,
    sortOrder,
    setSortOrder,
    sourceFilter,
    setSourceFilter,
    downloadingId,
    setDownloadingId,
    filtersExpanded,
    setFiltersExpanded,
    normalizedQuery,
    seasonToken,
    seasonInQuery,
    search,
    download,
    inputRef,
    sources,
    visibleResults,
    handleSubmit,
    handleClear,
    t,
  };
}
