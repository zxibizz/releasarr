import { notifications } from '@mantine/notifications';
import { useMutation } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { releasesApi } from '@/features/releases/api';
import {
  confirmExistingReleases,
  existingReleaseIdsFromError,
  isExistingReleasesDecisionRequired,
} from '@/features/releases/existingReleases';
import { useReleasesByRequest } from '@/features/releases/queries';
import type {
  AsyncOperationResponse,
  ExistingReleasesAction,
  IndexerSearchFailure,
  ReleaseSearchResult,
  SearchIndexer,
} from '@/types';
import { getErrorMessage } from '@/utils/errors';
import { daysSince } from '@/utils/formatters';

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

export const ageInDays = (candidate: ReleaseSearchResult): number | null =>
  daysSince(candidate.publish_date);

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
  const [failedIndexers, setFailedIndexers] = useState<IndexerSearchFailure[]>([]);
  const [searchedQuery, setSearchedQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>(DEFAULT_SORT_FIELD);
  const [sortOrder, setSortOrder] = useState<SortOrder>(NATURAL_SORT_ORDER[DEFAULT_SORT_FIELD]);
  const [sourceFilter, setSourceFilter] = useState(DEFAULT_SOURCE_FILTER);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [pendingIndexers, setPendingIndexers] = useState<SearchIndexer[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<unknown>(null);
  const searchController = useRef<AbortController | null>(null);

  const normalizedQuery = query.replace(/\s+/g, ' ').trim();
  const seasonToken = seasonNumber === undefined ? null : String(seasonNumber);
  const seasonInQuery = Boolean(
    seasonToken && new RegExp(`(^|\\s)${seasonToken}(\\s|$)`, 'i').test(normalizedQuery),
  );

  const { data: existingReleases } = useReleasesByRequest(requestId);

  const cancelSearch = () => {
    searchController.current?.abort();
    searchController.current = null;
    setPendingIndexers([]);
    setIsSearching(false);
  };

  useEffect(() => () => searchController.current?.abort(), []);

  const reportSearchFailure = (error: unknown) => {
    setSearchError(error);
    notifications.show({
      title: t('releaseSearch.toasts.searchFailedTitle'),
      message: getErrorMessage(error, t('releaseSearch.toasts.searchFailedFallback')),
      color: 'red',
    });
  };

  // Each indexer is searched on its own and its results shown as soon as it
  // answers. Searched together, the slowest indexer held back every result:
  // some trackers take half a minute on any query.
  const runSearch = async (value: string) => {
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    const { signal } = controller;

    setResults([]);
    setFailedIndexers([]);
    setSearchError(null);
    setSearchedQuery(value);
    setIsSearching(true);

    let indexers: SearchIndexer[];
    try {
      indexers = await releasesApi.searchIndexers(signal);
    } catch (error) {
      if (signal.aborted) return;
      setIsSearching(false);
      reportSearchFailure(error);
      return;
    }
    if (signal.aborted) return;
    setPendingIndexers(indexers);

    const errors: unknown[] = [];
    await Promise.all(
      indexers.map(async (indexer) => {
        try {
          const response = await releasesApi.search(value, requestId, signal, indexer.indexer_id);
          if (signal.aborted) return;
          const found = response.results ?? [];
          setResults((current) => [
            ...current,
            ...found.filter(
              (result) => !current.some((item) => item.release_id === result.release_id),
            ),
          ]);
          const failures = response.failed_indexers ?? [];
          if (failures.length > 0) setFailedIndexers((current) => [...current, ...failures]);
        } catch (error) {
          if (signal.aborted) return;
          errors.push(error);
          setFailedIndexers((current) => [
            ...current,
            {
              indexer_id: indexer.indexer_id,
              name: indexer.name,
              reason: getErrorMessage(error, t('releaseSearch.toasts.searchFailedFallback')),
            },
          ]);
        } finally {
          if (!signal.aborted) {
            setPendingIndexers((current) =>
              current.filter((item) => item.indexer_id !== indexer.indexer_id),
            );
          }
        }
      }),
    );
    if (signal.aborted) return;

    searchController.current = null;
    setIsSearching(false);
    // Nothing answered at all: the request itself is failing, not a tracker.
    if (indexers.length > 0 && errors.length === indexers.length) {
      setFailedIndexers([]);
      reportSearchFailure(errors[0]);
    }
  };

  const search = {
    mutate: (value: string) => void runSearch(value),
    isPending: isSearching,
    isError: searchError !== null,
    error: searchError,
  };

  // Cancelling resolves with `null` rather than throwing, so it never shows as
  // a failed grab - the user simply changed their mind.
  const download = useMutation({
    mutationFn: async (candidate: ReleaseSearchResult): Promise<AsyncOperationResponse | null> => {
      const attempt = async (
        decision?: ExistingReleasesAction,
      ): Promise<AsyncOperationResponse | null> => {
        try {
          return await releasesApi.queueDownload(requestId, {
            release_id: candidate.release_id,
            existing_releases: decision,
          });
        } catch (error) {
          // The cached release list can be stale; the server is the source of truth.
          if (decision === undefined && isExistingReleasesDecisionRequired(error)) {
            const releaseIds = existingReleaseIdsFromError(error);
            const relevant = (existingReleases ?? []).filter((release) =>
              releaseIds.includes(release.id),
            );
            const chosen = await confirmExistingReleases(
              relevant.length > 0 ? relevant : (existingReleases ?? []),
              t,
            );
            return chosen === null ? null : attempt(chosen);
          }
          throw error;
        }
      };

      if ((existingReleases ?? []).length > 0) {
        const chosen = await confirmExistingReleases(existingReleases ?? [], t);
        return chosen === null ? null : attempt(chosen);
      }

      return attempt();
    },
    onSuccess: (response, candidate) => {
      if (response === null) {
        return;
      }
      notifications.show({
        title: t('releaseSearch.toasts.downloadQueuedTitle'),
        message:
          response?.message ??
          t('releaseSearch.toasts.downloadQueuedFallback', { name: candidate.release_name }),
        color: 'teal',
      });
      cancelSearch();
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
    cancelSearch();
    setSearchError(null);
    setQuery('');
    setResults([]);
    setFailedIndexers([]);
    setSearchedQuery('');
    setSourceFilter(DEFAULT_SOURCE_FILTER);
  };

  const dismissFailedIndexers = () => setFailedIndexers([]);

  return {
    activeTab,
    setActiveTab,
    query,
    setQuery,
    results,
    failedIndexers,
    dismissFailedIndexers,
    pendingIndexers,
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
