import {
  ActionIcon,
  Alert,
  Button,
  Collapse,
  Divider,
  Group,
  Indicator,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconAdjustmentsHorizontal, IconRefresh, IconSearch } from '@tabler/icons-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { StatusBadge } from '@/components/StatusBadge';
import { RequestCard } from '@/features/requests/components/RequestCard';
import {
  DEFAULT_SORT,
  FILTER_KEYS,
  SORT_KEYS,
  buildStats,
  filterAndSortRequests,
  type FilterKey,
  type SortKey,
} from '@/features/requests/filtering';
import { localizeRequest, useLanguageSelection } from '@/features/requests/localization';
import { useRequestsList } from '@/features/requests/queries';
import { useRequestFilters } from '@/features/requests/useRequestFilters';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequestStatus } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const FILTER_LABEL_KEYS: Record<string, string> = {
  all: 'requestsList.filters.all',
  movies: 'requestsList.filters.movies',
  series: 'requestsList.filters.series',
};

function RequestsSkeleton() {
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
      {Array.from({ length: 4 }).map((_, index) => (
        <Paper key={index} withBorder radius="lg" p="lg">
          <Stack gap="sm">
            <Skeleton height={20} width="60%" />
            <Skeleton height={12} />
            <Skeleton height={12} width="80%" />
            <Skeleton height={28} width={120} radius="xl" />
          </Stack>
        </Paper>
      ))}
    </SimpleGrid>
  );
}

/**
 * Eight filters wrap onto three rows on a phone and push the list off screen, so
 * they scroll sideways as a single row instead.
 */
function FilterPills({
  filter,
  onSelect,
  label,
}: {
  filter: FilterKey;
  onSelect: (key: FilterKey) => void;
  label: (key: string) => string;
}) {
  const isMobile = useIsMobile();

  const pills = (
    <Group
      gap="xs"
      wrap={isMobile ? 'nowrap' : 'wrap'}
      // Sized to its content so the row overflows the scroller instead of
      // squeezing every pill down to a single letter.
      w={isMobile ? 'max-content' : undefined}
    >
      {FILTER_KEYS.map((key) => (
        <Button
          key={key}
          size="xs"
          radius="xl"
          variant={filter === key ? 'filled' : 'default'}
          onClick={() => onSelect(key)}
          style={{ flexShrink: 0 }}
        >
          {label(key)}
        </Button>
      ))}
    </Group>
  );

  if (!isMobile) {
    return pills;
  }

  return (
    <ScrollArea type="never" offsetScrollbars={false}>
      {pills}
    </ScrollArea>
  );
}

interface RequestFiltersProps {
  filter: FilterKey;
  setFilter: (key: FilterKey) => void;
  filterLabel: (key: string) => string;
  search: string;
  setSearch: (value: string) => void;
  sort: SortKey;
  setSort: (value: SortKey) => void;
  language: string | null;
  setLanguage: (value: string | null) => void;
  availableLanguages: string[];
}

/**
 * The pills plus three labelled fields filled a phone screen on their own. Only
 * the pills and the search box stay out in the open here; sort and metadata
 * language move behind a toggle, marked with a dot while either is set so a
 * non-default sort is never hidden silently.
 */
function RequestFilters({
  filter,
  setFilter,
  filterLabel,
  search,
  setSearch,
  sort,
  setSort,
  language,
  setLanguage,
  availableLanguages,
}: RequestFiltersProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [expanded, { toggle }] = useDisclosure(false);

  const searchInput = (
    <TextInput
      // The label repeated the placeholder verbatim, so on a phone it only cost
      // a line; the magnifier carries the same meaning in less space.
      label={isMobile ? undefined : t('requestsList.searchPlaceholder')}
      placeholder={t('requestsList.searchPlaceholder')}
      aria-label={t('requestsList.searchPlaceholder')}
      leftSection={isMobile ? <IconSearch size={16} /> : undefined}
      type="search"
      enterKeyHint="search"
      value={search}
      onChange={(event) => setSearch(event.currentTarget.value)}
      style={isMobile ? { flex: 1, minWidth: 0 } : undefined}
      w={isMobile ? undefined : 260}
    />
  );

  const sortSelect = (
    <Select
      label={t('requestsList.sortAriaLabel')}
      value={sort}
      onChange={(value) => value && setSort(value as SortKey)}
      allowDeselect={false}
      data={SORT_KEYS.map((key) => ({ value: key, label: t(`requestsList.sort.${key}`) }))}
      w={{ base: '100%', sm: 200 }}
    />
  );

  const languageSelect = availableLanguages.length > 0 && (
    <Select
      label={t('localization.selectorLabel')}
      value={language ?? 'default'}
      onChange={(value) => setLanguage(value === 'default' ? null : value)}
      allowDeselect={false}
      data={[
        { value: 'default', label: t('localization.defaultOption') },
        ...availableLanguages.map((code) => ({
          value: code,
          label: t(`localization.languageNames.${code}`, { defaultValue: code.toUpperCase() }),
        })),
      ]}
      w={{ base: '100%', sm: 180 }}
    />
  );

  if (!isMobile) {
    return (
      <Stack gap="md">
        <FilterPills filter={filter} onSelect={setFilter} label={filterLabel} />
        <Group align="flex-end" gap="sm" wrap="wrap">
          {searchInput}
          {sortSelect}
          {languageSelect}
        </Group>
      </Stack>
    );
  }

  const adjusted = sort !== DEFAULT_SORT || language !== null;

  return (
    <Stack gap="xs">
      <FilterPills filter={filter} onSelect={setFilter} label={filterLabel} />

      <Group gap="xs" wrap="nowrap" align="center">
        {searchInput}
        <Indicator disabled={!adjusted} size={8} offset={4}>
          <ActionIcon
            variant={expanded ? 'filled' : 'default'}
            size="lg"
            aria-label={t('requestsList.moreFilters')}
            aria-expanded={expanded}
            onClick={toggle}
          >
            <IconAdjustmentsHorizontal size={18} />
          </ActionIcon>
        </Indicator>
      </Group>

      {/*
        Unmounted while closed so the hidden selects stay out of the tab order;
        both read their value from the URL, so there is no state to preserve.
      */}
      <Collapse expanded={expanded} keepMounted={false}>
        <Stack gap="sm" pt="xs">
          {sortSelect}
          {languageSelect}
        </Stack>
      </Collapse>
    </Stack>
  );
}

export function RequestsPage() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { filter, sort, search, setFilter, setSort, setSearch } = useRequestFilters();
  const { requests, isLoading, isFetching, error, refetch } = useRequestsList();
  const { availableLanguages, language, setLanguage } = useLanguageSelection(requests);

  const localizedRequests = useMemo(
    () => requests.map((request) => localizeRequest(request, language)),
    [requests, language],
  );

  const visibleRequests = useMemo(
    () => filterAndSortRequests(localizedRequests, { filter, sort, search }),
    [localizedRequests, filter, sort, search],
  );

  const stats = useMemo(() => buildStats(requests), [requests]);

  const filterLabel = (key: string) =>
    FILTER_LABEL_KEYS[key] ? t(FILTER_LABEL_KEYS[key]) : t(`status.${key}`);

  if (isLoading && requests.length === 0) {
    return (
      <Stack gap="xl">
        <Skeleton height={36} width={240} />
        <RequestsSkeleton />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="red" title={t('requestsList.error.title')} radius="lg">
        <Stack align="flex-start" gap="sm">
          <Text>{getErrorMessage(error, t('requestsList.error.description'))}</Text>
          <Button variant="light" size="xs" onClick={() => void refetch()}>
            {t('common.tryAgain')}
          </Button>
        </Stack>
      </Alert>
    );
  }

  return (
    // `xl` gaps between five stacked sections cost a quarter of a phone screen.
    <Stack gap={isMobile ? 'md' : 'xl'}>
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
        <Stack gap={4} style={{ minWidth: 0 }}>
          <Title order={1}>{t('requestsList.title')}</Title>
          {/* The subtitle only restates the title, which a phone can't spare two lines for. */}
          {!isMobile && <Text c="dimmed">{t('requestsList.subtitle')}</Text>}
        </Stack>

        {/* There is no pull-to-refresh here, so reloading needs a control. */}
        <Tooltip label={t('common.refresh')}>
          <ActionIcon
            variant="light"
            size="lg"
            aria-label={t('common.refresh')}
            loading={isFetching}
            onClick={() => void refetch()}
          >
            <IconRefresh size={18} />
          </ActionIcon>
        </Tooltip>
      </Group>

      <RequestFilters
        filter={filter}
        setFilter={setFilter}
        filterLabel={filterLabel}
        search={search}
        setSearch={setSearch}
        sort={sort}
        setSort={setSort}
        language={language}
        setLanguage={setLanguage}
        availableLanguages={availableLanguages}
      />

      <RequestStats stats={stats} />

      <Group justify="space-between" align="center">
        <Title order={3}>
          {filter === 'all'
            ? t('requestsList.headings.all')
            : t('requestsList.headings.filtered', { label: filterLabel(filter) })}
        </Title>
        <Text c="dimmed" size="sm">
          {t('requestsList.resultsCount', { count: visibleRequests.length })}
        </Text>
      </Group>

      {requests.length === 0 ? (
        <EmptyState
          icon="📺"
          title={t('requestsList.empty.title')}
          description={t('requestsList.empty.description')}
        />
      ) : visibleRequests.length === 0 ? (
        <EmptyState
          icon="🧭"
          title={t('requestsList.emptyFiltered.title')}
          description={t('requestsList.emptyFiltered.description')}
        />
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
          {visibleRequests.map((request) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
}

function RequestStats({ stats }: { stats: ReturnType<typeof buildStats> }) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  const breakdown = (
    <Group
      gap="xs"
      wrap={isMobile ? 'nowrap' : 'wrap'}
      w={isMobile ? 'max-content' : undefined}
      py={isMobile ? 2 : undefined}
    >
      {(Object.keys(stats.byStatus) as MediaRequestStatus[]).map((status) => (
        <Group key={status} gap={6} style={{ flexShrink: 0 }}>
          <StatusBadge status={status} size="sm" />
          <Text size="sm" c="dimmed">
            {stats.byStatus[status]}
          </Text>
        </Group>
      ))}
    </Group>
  );

  if (isMobile) {
    /*
     * The four headline totals cost roughly a third of a phone screen to repeat
     * numbers already on it: the total matches the result count above the list,
     * and the movie/series split is one tap away on the pills. Only the
     * per-status breakdown is unique, so only it survives.
     */
    return <ScrollArea type="never">{breakdown}</ScrollArea>;
  }

  return (
    <Paper withBorder radius="lg" p="md">
      <Stack gap="sm">
        <SimpleGrid cols={{ base: 2, md: 4 }}>
          <Stat label={t('requestsList.stats.total')} value={stats.total} />
          <Stat label={t('requestsList.stats.movies')} value={stats.byType.movie ?? 0} />
          <Stat label={t('requestsList.stats.series')} value={stats.byType.series ?? 0} />
          <Stat label={t('requestsList.stats.completed')} value={stats.byStatus.completed ?? 0} />
        </SimpleGrid>
        <Divider />
        {breakdown}
      </Stack>
    </Paper>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Stack gap={2}>
      <Text size="xs" c="dimmed" tt="uppercase">
        {label}
      </Text>
      <Text fz={26} fw={700}>
        {value}
      </Text>
    </Stack>
  );
}
