import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Collapse,
  Group,
  Indicator,
  Paper,
  Select,
  Skeleton,
  Stack,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconAdjustmentsHorizontal } from '@tabler/icons-react';
import { useMutation } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { releasesApi } from '@/features/releases/api';
import { ManualReleaseForm } from '@/features/releases/components/ManualReleaseForm';
import { useIsMobile } from '@/hooks/useIsMobile';
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

const DEFAULT_SORT_FIELD: SortField = 'age';
const DEFAULT_SOURCE_FILTER = 'all';

const SEARCH_TAB = 'search';
const MANUAL_TAB = 'manual';

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
  const isMobile = useIsMobile();
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  // The phone renders a textarea and the desktop an input, so the ref is
  // assigned by hand rather than typed to one element.
  const assignInputRef = (node: HTMLInputElement | HTMLTextAreaElement | null) => {
    inputRef.current = node;
  };

  // Only stretch the actions on a phone; growing them on desktop shrinks the
  // labels below their content width and clips them.
  const actionFlex = isMobile ? 1 : undefined;

  const ageLabel = (days: number | null): string => {
    if (days === null) return t('releaseSearch.age.unknown');
    if (days < 1) return t('releaseSearch.age.today');
    return t('releaseSearch.age.days', { count: Math.floor(days) });
  };

  const [activeTab, setActiveTab] = useState<string>(SEARCH_TAB);
  const [query, setQuery] = useState(prefillQuery ?? '');
  const [results, setResults] = useState<ReleaseSearchResult[]>([]);
  const [searchedQuery, setSearchedQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>(DEFAULT_SORT_FIELD);
  const [sortOrder, setSortOrder] = useState<SortOrder>(NATURAL_SORT_ORDER[DEFAULT_SORT_FIELD]);
  const [sourceFilter, setSourceFilter] = useState(DEFAULT_SOURCE_FILTER);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [filtersExpanded, { toggle: toggleFilters }] = useDisclosure(false);

  // The field wraps over several lines on a phone, and an indexer has no use
  // for the line breaks that puts in the query.
  const normalizedQuery = query.replace(/\s+/g, ' ').trim();

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

  // The request page's "Manual search" action expects the query field, so it
  // pulls the search tab back to the front if the manual one is showing.
  const [lastFocusToken, setLastFocusToken] = useState(focusToken);
  if (focusToken !== lastFocusToken) {
    setLastFocusToken(focusToken);
    if (focusToken > 0) {
      setActiveTab(SEARCH_TAB);
    }
  }

  // Focus is the browser's to give, not React's, so it stays in an effect and
  // runs after the tab above has had its chance to mount the field.
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
    if (normalizedQuery) {
      search.mutate(normalizedQuery);
    }
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    setSearchedQuery('');
    setSourceFilter(DEFAULT_SOURCE_FILTER);
  };

  // Anything a collapsed panel is hiding shows as a dot on the toggle, so a
  // narrowed or reordered result list is never unexplained.
  const filtersAdjusted =
    sortField !== DEFAULT_SORT_FIELD ||
    sortOrder !== NATURAL_SORT_ORDER[DEFAULT_SORT_FIELD] ||
    sourceFilter !== DEFAULT_SOURCE_FILTER;

  const filterControls = (
    <Group gap="sm" wrap="wrap">
      <Select
        label={t('releaseSearch.sort.label')}
        size="xs"
        w={{ base: '47%', sm: 150 }}
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
        w={{ base: '47%', sm: 140 }}
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
          w={{ base: '100%', sm: 170 }}
          allowDeselect={false}
          value={sourceFilter}
          onChange={(value) => value && setSourceFilter(value)}
          data={[
            { value: DEFAULT_SOURCE_FILTER, label: t('releaseSearch.filters.source.all') },
            ...sources.map((source) => ({ value: source, label: source })),
          ]}
        />
      )}
    </Group>
  );

  return (
    <Card withBorder radius="lg" padding={isMobile ? 'sm' : 'lg'}>
      <Tabs value={activeTab} onChange={(value) => setActiveTab(value ?? SEARCH_TAB)}>
        {/* Long labels wrapped the list into two stacked rows on a phone,
            which read as two links rather than one tab bar. */}
        <Tabs.List grow mb="lg">
          <Tabs.Tab value={SEARCH_TAB}>{t('releaseSearch.tabs.search')}</Tabs.Tab>
          <Tabs.Tab value={MANUAL_TAB}>{t('releaseSearch.tabs.manual')}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value={SEARCH_TAB}>
          <Stack gap="lg">
            <form onSubmit={handleSubmit}>
              <Group align="flex-end" gap="sm" wrap="wrap">
                {isMobile ? (
                  /*
                    Queries here are whole release titles — the prefilled
                    request title alone outruns a phone-width field, and a
                    single line hid everything but its first few words behind a
                    horizontal scroll. The field grows to show the query
                    instead, up to four lines.
                  */
                  <Textarea
                    ref={assignInputRef}
                    autosize
                    minRows={1}
                    maxRows={4}
                    w="100%"
                    value={query}
                    onChange={(event) => setQuery(event.currentTarget.value)}
                    placeholder={t('releaseSearch.placeholder', { title: requestTitle })}
                    aria-label={t('releaseSearch.ariaLabel', { title: requestTitle })}
                  />
                ) : (
                  <TextInput
                    ref={assignInputRef}
                    type="search"
                    enterKeyHint="search"
                    style={{ flex: '1 1 220px', minWidth: 0 }}
                    value={query}
                    onChange={(event) => setQuery(event.currentTarget.value)}
                    placeholder={t('releaseSearch.placeholder', { title: requestTitle })}
                    aria-label={t('releaseSearch.ariaLabel', { title: requestTitle })}
                  />
                )}
                <Group gap="sm" wrap="nowrap" w={{ base: '100%', sm: 'auto' }}>
                  <Button
                    type="submit"
                    loading={search.isPending}
                    disabled={!normalizedQuery}
                    style={{ flex: actionFlex }}
                  >
                    {t('releaseSearch.actions.search')}
                  </Button>
                  {(query || results.length > 0) && (
                    <Button
                      type="button"
                      variant="default"
                      onClick={handleClear}
                      style={{ flex: actionFlex }}
                    >
                      {t('releaseSearch.actions.clear')}
                    </Button>
                  )}
                </Group>
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
                <Group justify="space-between" wrap="wrap" gap="xs">
                  <Title order={5}>{t('releaseSearch.results.heading')}</Title>
                  <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
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
                    {isMobile && (
                      <Indicator disabled={!filtersAdjusted} size={8} offset={4}>
                        <ActionIcon
                          variant={filtersExpanded ? 'filled' : 'default'}
                          size="lg"
                          // The dot is only visual, so the label carries the same news.
                          aria-label={t(
                            filtersAdjusted
                              ? 'releaseSearch.filters.toggleActive'
                              : 'releaseSearch.filters.toggle',
                          )}
                          aria-expanded={filtersExpanded}
                          onClick={toggleFilters}
                        >
                          <IconAdjustmentsHorizontal size={18} />
                        </ActionIcon>
                      </Indicator>
                    )}
                  </Group>
                </Group>

                {/*
                  Two rows of sort and source controls on a phone pushed the
                  candidates themselves below the fold, and the default order —
                  freshest first, every source — is the one wanted almost every
                  time. Unmounted while closed so the hidden controls stay out
                  of the tab order.
                */}
                {isMobile ? (
                  <Collapse expanded={filtersExpanded} keepMounted={false}>
                    {filterControls}
                  </Collapse>
                ) : (
                  filterControls
                )}

                <Stack gap="sm">
                  {visibleResults.map((candidate) => {
                    const quality = candidate.quality;
                    const age = ageInDays(candidate);
                    const publishedAt = candidate.publish_date
                      ? formatDateTime(candidate.publish_date)
                      : null;
                    return (
                      <Paper
                        key={candidate.release_id}
                        withBorder
                        radius="md"
                        p={{ base: 'sm', sm: 'md' }}
                      >
                        <Group justify="space-between" align="center" wrap="wrap" gap="md">
                          <Stack gap={6} style={{ flex: '1 1 240px', minWidth: 0 }}>
                            {/*
                              The name is the whole basis for picking one
                              candidate over another — group, resolution, audio
                              tracks and release tags all live in its tail — so
                              it wraps in full rather than being clamped.
                            */}
                            <Text size="sm" fw={600} className="break-anywhere">
                              {candidate.release_name}
                            </Text>
                            <Group gap="sm" fz="xs" c="dimmed" wrap="wrap">
                              {/* An indexer that reported no quality gets no
                                  badge: "Unknown" named the gap without
                                  narrowing it. */}
                              {quality && (
                                <Badge
                                  size="sm"
                                  radius="xl"
                                  variant="light"
                                  color={QUALITY_COLORS[quality] ?? 'gray'}
                                >
                                  {quality}
                                </Badge>
                              )}
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
                            w={{ base: '100%', sm: 'auto' }}
                            loading={downloadingId === candidate.release_id}
                            disabled={
                              Boolean(downloadingId) && downloadingId !== candidate.release_id
                            }
                            aria-label={t('releaseSearch.actions.queueDownload', {
                              name: candidate.release_name,
                            })}
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
              <Paper withBorder radius="lg" p={{ base: 'md', sm: 'xl' }}>
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
        </Tabs.Panel>

        <Tabs.Panel value={MANUAL_TAB}>
          <ManualReleaseForm requestId={requestId} onDownloadQueued={onDownloadQueued} />
        </Tabs.Panel>
      </Tabs>
    </Card>
  );
}
