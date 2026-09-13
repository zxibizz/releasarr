import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Collapse,
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
import { IconAdjustmentsHorizontal, IconPlus, IconRefresh, IconSearch } from '@tabler/icons-react';
import { useMemo, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { RequestCard } from '@/features/requests/components/RequestCard';
import {
  DEFAULT_SORT,
  DEFAULT_STATUS,
  DEFAULT_TYPE,
  SORT_KEYS,
  STATUS_KEYS,
  TYPE_KEYS,
  filterAndSortRequests,
  type SortKey,
  type StatusFilter,
  type TypeFilter,
} from '@/features/requests/filtering';
import { localizeRequest, useMetadataLanguage } from '@/features/requests/localization';
import { useRequestsList } from '@/features/requests/queries';
import { useRequestFilters } from '@/features/requests/useRequestFilters';
import { useIsMobile } from '@/hooks/useIsMobile';
import { getErrorMessage } from '@/utils/errors';

const TYPE_LABEL_KEYS: Record<TypeFilter, string> = {
  all: 'requestsList.filters.all',
  movie: 'requestsList.filters.movies',
  series: 'requestsList.filters.series',
};

/** Statuses that aren't a single `MediaRequestStatus` need their own wording. */
const STATUS_LABEL_KEYS: Partial<Record<StatusFilter, string>> = {
  active: 'requestsList.filters.active',
  all: 'requestsList.filters.anyStatus',
};

const HEADING_KEYS: Partial<Record<StatusFilter, string>> = {
  active: 'requestsList.headings.active',
  all: 'requestsList.headings.all',
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
 * Names the dimension a row of controls belongs to. Both filters offer an "all"
 * option, so without the label a phone would show two identical pills. The label
 * sits beside the control rather than above it to cost no vertical space, and
 * the two share a fixed width so the controls line up.
 */
function FilterRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Group gap="sm" wrap="nowrap" align="center">
      <Text size="xs" c="dimmed" tt="uppercase" w={58} style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Box style={{ flex: 1, minWidth: 0 }}>{children}</Box>
    </Group>
  );
}

/**
 * One control for both filter rows: type and status ask the same kind of
 * question — pick one of these — and answering them through two different
 * widgets made the pair read as unrelated.
 *
 * Seven statuses wrap onto three rows on a phone and push the list off screen,
 * so the pills scroll sideways as a single row instead.
 */
function FilterPills<T extends string>({
  value,
  options,
  onSelect,
  label,
}: {
  value: T;
  options: readonly T[];
  onSelect: (key: T) => void;
  label: (key: T) => string;
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
      {options.map((key) => (
        <Button
          key={key}
          size="xs"
          radius="xl"
          variant={value === key ? 'filled' : 'default'}
          // A filled pill is the only visual mark of the current choice, so
          // the pressed state has to be announced as well.
          aria-pressed={value === key}
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
  type: TypeFilter;
  setType: (key: TypeFilter) => void;
  typeLabel: (key: TypeFilter) => string;
  status: StatusFilter;
  setStatus: (key: StatusFilter) => void;
  statusLabel: (key: StatusFilter) => string;
  search: string;
  setSearch: (value: string) => void;
  sort: SortKey;
  setSort: (value: SortKey) => void;
}

/**
 * Search stays out in the open; type, status and sort sit behind a toggle. The
 * default list is the one wanted almost every time, and three rows of controls
 * standing above it earned less than the vertical space they cost — on a desktop
 * as much as on a phone. The toggle carries a dot while any hidden control is
 * set, so a narrowed list is never unexplained.
 */
function RequestFilters({
  type,
  setType,
  typeLabel,
  status,
  setStatus,
  statusLabel,
  search,
  setSearch,
  sort,
  setSort,
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

  const typeRow = (
    <FilterRow label={t('requestsList.filters.typeLabel')}>
      <FilterPills value={type} options={TYPE_KEYS} onSelect={setType} label={typeLabel} />
    </FilterRow>
  );
  const statusRow = (
    <FilterRow label={t('requestsList.filters.statusLabel')}>
      <FilterPills value={status} options={STATUS_KEYS} onSelect={setStatus} label={statusLabel} />
    </FilterRow>
  );

  const adjusted = type !== DEFAULT_TYPE || status !== DEFAULT_STATUS || sort !== DEFAULT_SORT;

  return (
    <Stack gap="xs">
      {/* Only the phone's search box drops its label, so only there do the two
          controls share a baseline. */}
      <Group gap="xs" wrap="nowrap" align={isMobile ? 'center' : 'flex-end'}>
        {searchInput}
        <Indicator disabled={!adjusted} size={8} offset={4}>
          <ActionIcon
            variant={expanded ? 'filled' : 'default'}
            size="lg"
            // The dot is only visual, so the label carries the same news.
            aria-label={t(
              adjusted ? 'requestsList.filtersToggleActive' : 'requestsList.filtersToggle',
            )}
            aria-expanded={expanded}
            onClick={toggle}
          >
            <IconAdjustmentsHorizontal size={18} />
          </ActionIcon>
        </Indicator>
      </Group>

      {/*
        Unmounted while closed so the hidden controls stay out of the tab order —
        all of them read their value from the URL, so there is no state to
        preserve.
      */}
      <Collapse expanded={expanded} keepMounted={false}>
        <Stack gap="sm" pt="xs">
          {typeRow}
          {statusRow}
          {sortSelect}
        </Stack>
      </Collapse>
    </Stack>
  );
}

export function RequestsPage() {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const { type, status, sort, search, setType, setStatus, setSort, setSearch } =
    useRequestFilters();
  const { requests, isLoading, isFetching, error, refetch } = useRequestsList();
  const metadataLanguage = useMetadataLanguage();

  const localizedRequests = useMemo(
    () => requests.map((request) => localizeRequest(request, metadataLanguage)),
    [requests, metadataLanguage],
  );

  const visibleRequests = useMemo(
    () => filterAndSortRequests(localizedRequests, { type, status, sort, search }),
    [localizedRequests, type, status, sort, search],
  );

  const typeLabel = (key: TypeFilter) => t(TYPE_LABEL_KEYS[key]);
  const statusLabel = (key: StatusFilter) => {
    const labelKey = STATUS_LABEL_KEYS[key];
    return labelKey ? t(labelKey) : t(`status.${key}`);
  };

  // The statuses that aren't a single `MediaRequestStatus` read badly through the
  // "{{label}} Requests" template, so they name the list themselves. A chosen
  // type qualifies whichever heading results.
  const headingKey = HEADING_KEYS[status];
  const statusHeading = headingKey
    ? t(headingKey)
    : t('requestsList.headings.filtered', { label: statusLabel(status) });
  const heading =
    type === 'all'
      ? statusHeading
      : t('requestsList.headings.withType', {
          status: statusHeading,
          type: typeLabel(type),
        });

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
    // `xl` gaps between four stacked sections cost a quarter of a phone screen.
    <Stack gap={isMobile ? 'md' : 'xl'}>
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
        <Stack gap={4} style={{ minWidth: 0 }}>
          <Title order={1}>{t('requestsList.title')}</Title>
          {/* The subtitle only restates the title, which a phone can't spare two lines for. */}
          {!isMobile && <Text c="dimmed">{t('requestsList.subtitle')}</Text>}
        </Stack>

        <Group gap="xs" wrap="nowrap">
          {/* The label is the point of the button, so a phone keeps the icon only. */}
          <Button
            component={Link}
            to="/add"
            size={isMobile ? 'compact-sm' : 'sm'}
            leftSection={<IconPlus size={16} />}
          >
            {isMobile ? t('discover.actions.addShort') : t('discover.actions.add')}
          </Button>

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
      </Group>

      <RequestFilters
        type={type}
        setType={setType}
        typeLabel={typeLabel}
        status={status}
        setStatus={setStatus}
        statusLabel={statusLabel}
        search={search}
        setSearch={setSearch}
        sort={sort}
        setSort={setSort}
      />

      <Group justify="space-between" align="center">
        <Title order={3}>{heading}</Title>
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
