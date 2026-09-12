import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Group,
  Paper,
  Select,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { releasesApi } from '@/features/releases/api';
import type { ReleaseSearchResult } from '@/types';
import { getErrorMessage } from '@/utils/errors';
import { formatDateTime } from '@/utils/formatters';

const QUALITY_COLORS: Record<string, string> = {
  '2160p': 'grape',
  '1080p': 'blue',
  '720p': 'teal',
};

type SortField = 'age' | 'seeders' | 'leechers' | 'size';
type SortOrder = 'desc' | 'asc';

const SORT_FIELDS: SortField[] = ['age', 'seeders', 'leechers', 'size'];

/**
 * Each field has a different "most useful first" direction: freshest releases
 * mean the lowest age, while more seeders/leechers/bytes mean the highest value.
 */
const NATURAL_SORT_ORDER: Record<SortField, SortOrder> = {
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
  if (!match) {
    return null;
  }
  const value = Number.parseFloat(match[1]);
  const multiplier = SIZE_MULTIPLIERS[match[2].toUpperCase()];
  return Number.isNaN(value) || !multiplier ? null : value * multiplier;
};

/** Age of a release in days, or null when the indexer reported no publish date. */
const ageInDays = (candidate: ReleaseSearchResult): number | null => {
  if (!candidate.publish_date) {
    return null;
  }
  const published = new Date(candidate.publish_date).getTime();
  if (Number.isNaN(published)) {
    return null;
  }
  return Math.max(0, (Date.now() - published) / DAY_IN_MS);
};

const sortValue = (candidate: ReleaseSearchResult, field: SortField): number | null => {
  if (field === 'age') return ageInDays(candidate);
  if (field === 'seeders') return candidate.seeders ?? null;
  if (field === 'leechers') return candidate.leechers ?? null;
  return parseSizeToBytes(candidate.size);
};

interface ReleaseSearchProps {
  requestId: string;
  requestTitle: string;
  prefillQuery?: string;
  focusToken?: number;
  onDownloadQueued: () => void;
}

export function ReleaseSearch({
  requestId,
  requestTitle,
  prefillQuery,
  focusToken = 0,
  onDownloadQueued,
}: ReleaseSearchProps) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);

  const ageLabel = (days: number | null): string => {
    if (days === null) return t('releaseSearch.age.unknown');
    if (days < 1) return t('releaseSearch.age.today');
    return t('releaseSearch.age.days', { count: Math.floor(days) });
  };

  const [query, setQuery] = useState(prefillQuery ?? '');
  const [results, setResults] = useState<ReleaseSearchResult[]>([]);
  const [searchedQuery, setSearchedQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('age');
  const [sortOrder, setSortOrder] = useState<SortOrder>(NATURAL_SORT_ORDER.age);
  const [sourceFilter, setSourceFilter] = useState('all');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

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

  // Re-seed the input when the prefill changes (e.g. a different localization).
  const [lastPrefill, setLastPrefill] = useState(prefillQuery);
  if (prefillQuery !== lastPrefill) {
    setLastPrefill(prefillQuery);
    setQuery(prefillQuery ?? '');
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
      sourceFilter === 'all' ? results : results.filter((r) => r.source === sourceFilter);

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
    const trimmed = query.trim();
    if (trimmed) {
      search.mutate(trimmed);
    }
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setSearchedQuery('');
    setSourceFilter('all');
  };

  return (
    <Card withBorder radius="lg" padding="lg">
      <Stack gap="lg">
        <Title order={4}>{t('releaseSearch.title')}</Title>

        <form onSubmit={handleSubmit}>
          <Group align="flex-end" gap="sm" wrap="wrap">
            <TextInput
              ref={inputRef}
              style={{ flex: 1, minWidth: 220 }}
              value={query}
              onChange={(event) => setQuery(event.currentTarget.value)}
              placeholder={t('releaseSearch.placeholder', { title: requestTitle })}
              aria-label={t('releaseSearch.ariaLabel', { title: requestTitle })}
            />
            <Button type="submit" loading={search.isPending} disabled={!query.trim()}>
              {t('releaseSearch.actions.search')}
            </Button>
            {(query || results.length > 0) && (
              <Button type="button" variant="default" onClick={handleClear}>
                {t('releaseSearch.actions.clear')}
              </Button>
            )}
          </Group>
        </form>

        {search.isPending && (
          <Stack gap="sm">
            {Array.from({ length: 3 }).map((_, index) => (
              <Paper key={index} withBorder radius="md" p="md">
                <Skeleton height={14} width="70%" mb="xs" />
                <Skeleton height={10} width="40%" />
              </Paper>
            ))}
          </Stack>
        )}

        {search.isError && (
          <Alert color="red" radius="md">
            {getErrorMessage(search.error, t('releaseSearch.toasts.searchFailedFallback'))}
          </Alert>
        )}

        {visibleResults.length > 0 && (
          <Stack gap="md">
            <Group justify="space-between" wrap="wrap">
              <Title order={5}>{t('releaseSearch.results.heading')}</Title>
              <Text size="sm" c="dimmed">
                {t(
                  visibleResults.length === results.length
                    ? 'releaseSearch.results.summary'
                    : 'releaseSearch.results.summaryWithTotal',
                  {
                    count: visibleResults.length,
                    total: results.length,
                    query: searchedQuery,
                  },
                )}
              </Text>
            </Group>

            <Group gap="sm" wrap="wrap">
              <Select
                label={t('releaseSearch.sort.label')}
                size="xs"
                w={150}
                allowDeselect={false}
                value={sortField}
                onChange={(value) => {
                  if (!value) return;
                  const field = value as SortField;
                  setSortField(field);
                  setSortOrder(NATURAL_SORT_ORDER[field]);
                }}
                data={SORT_FIELDS.map((field) => ({
                  value: field,
                  label: t(`releaseSearch.sort.fields.${field}`),
                }))}
              />
              <Select
                label={t('releaseSearch.sort.directionLabel')}
                size="xs"
                w={140}
                allowDeselect={false}
                value={sortOrder}
                onChange={(value) => value && setSortOrder(value as SortOrder)}
                data={[
                  { value: 'desc', label: t('releaseSearch.sort.directions.desc') },
                  { value: 'asc', label: t('releaseSearch.sort.directions.asc') },
                ]}
              />
              {sources.length > 0 && (
                <Select
                  label={t('releaseSearch.filters.source.label')}
                  size="xs"
                  w={170}
                  allowDeselect={false}
                  value={sourceFilter}
                  onChange={(value) => value && setSourceFilter(value)}
                  data={[
                    { value: 'all', label: t('releaseSearch.filters.source.all') },
                    ...sources.map((source) => ({ value: source, label: source })),
                  ]}
                />
              )}
            </Group>

            <Stack gap="sm">
              {visibleResults.map((candidate) => {
                const quality = candidate.quality ?? t('releaseSearch.quality.unknown');
                const age = ageInDays(candidate);
                const publishedAt = candidate.publish_date
                  ? formatDateTime(candidate.publish_date)
                  : null;
                return (
                  <Paper key={candidate.release_id} withBorder radius="md" p="md">
                    <Group justify="space-between" align="center" wrap="wrap" gap="md">
                      <Stack gap={6} style={{ flex: 1, minWidth: 0 }}>
                        <Text size="sm" fw={600} lineClamp={2}>
                          {candidate.release_name}
                        </Text>
                        <Group gap="sm" fz="xs" c="dimmed" wrap="wrap">
                          <Badge
                            size="sm"
                            radius="xl"
                            variant="light"
                            color={QUALITY_COLORS[quality] ?? 'gray'}
                          >
                            {quality}
                          </Badge>
                          <Text size="xs" title={publishedAt ?? undefined}>
                            🕒 {ageLabel(age)}
                          </Text>
                          <Text size="xs">📦 {candidate.size}</Text>
                          <Text size="xs" c="teal">
                            ⬆️ {candidate.seeders ?? 0}
                          </Text>
                          <Text size="xs" c="red">
                            ⬇️ {candidate.leechers ?? 0}
                          </Text>
                          {candidate.source && <Text size="xs">🏷️ {candidate.source}</Text>}
                          {candidate.info_url && (
                            <Anchor
                              href={candidate.info_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              size="xs"
                            >
                              {t('releaseSearch.links.info')}
                            </Anchor>
                          )}
                        </Group>
                      </Stack>

                      <Button
                        size="xs"
                        loading={downloadingId === candidate.release_id}
                        disabled={Boolean(downloadingId) && downloadingId !== candidate.release_id}
                        onClick={() => {
                          setDownloadingId(candidate.release_id);
                          download.mutate(candidate);
                        }}
                      >
                        {t('releaseSearch.download')}
                      </Button>
                    </Group>
                  </Paper>
                );
              })}
            </Stack>
          </Stack>
        )}

        {searchedQuery && !search.isPending && visibleResults.length === 0 && (
          <Paper withBorder radius="lg" p="xl">
            <Stack align="center" gap="xs">
              <Text fz={32}>🔍</Text>
              <Title order={5}>{t('releaseSearch.empty.title')}</Title>
              <Text size="sm" c="dimmed" ta="center">
                {t('releaseSearch.empty.description')}
              </Text>
            </Stack>
          </Paper>
        )}
      </Stack>
    </Card>
  );
}
