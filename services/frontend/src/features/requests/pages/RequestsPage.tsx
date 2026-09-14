import {
  ActionIcon,
  Alert,
  Button,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Title,
  Tooltip,
} from '@mantine/core';
import { IconPlus, IconRefresh } from '@tabler/icons-react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { RequestCard } from '@/features/requests/components/RequestCard';
import { RequestFilters } from '@/features/requests/components/RequestFilters';
import { RequestsSkeleton } from '@/features/requests/components/RequestsSkeleton';
import {
  filterAndSortRequests,
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
