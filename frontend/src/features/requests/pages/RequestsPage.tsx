import {
  Alert,
  Button,
  Divider,
  Group,
  Loader,
  Paper,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { StatusBadge } from '@/components/StatusBadge';
import { RequestCard } from '@/features/requests/components/RequestCard';
import {
  FILTER_KEYS,
  SORT_KEYS,
  buildStats,
  filterAndSortRequests,
} from '@/features/requests/filtering';
import { localizeRequest, useLanguageSelection } from '@/features/requests/localization';
import { useRequestsList } from '@/features/requests/queries';
import { useRequestFilters } from '@/features/requests/useRequestFilters';
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

export function RequestsPage() {
  const { t } = useTranslation();
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
    <Stack gap="xl">
      <Stack gap={4}>
        <Title order={1}>{t('requestsList.title')}</Title>
        <Text c="dimmed">{t('requestsList.subtitle')}</Text>
      </Stack>

      <Stack gap="md">
        <Group gap="xs">
          {FILTER_KEYS.map((key) => (
            <Button
              key={key}
              size="xs"
              radius="xl"
              variant={filter === key ? 'filled' : 'default'}
              onClick={() => setFilter(key)}
            >
              {filterLabel(key)}
            </Button>
          ))}
        </Group>

        <Group align="flex-end" gap="sm" wrap="wrap">
          <TextInput
            label={t('requestsList.searchPlaceholder')}
            placeholder={t('requestsList.searchPlaceholder')}
            value={search}
            onChange={(event) => setSearch(event.currentTarget.value)}
            w={{ base: '100%', sm: 260 }}
          />

          <Select
            label={t('requestsList.sortAriaLabel')}
            value={sort}
            onChange={(value) => value && setSort(value as (typeof SORT_KEYS)[number])}
            allowDeselect={false}
            data={SORT_KEYS.map((key) => ({
              value: key,
              label: t(`requestsList.sort.${key}`),
            }))}
            w={{ base: '100%', sm: 200 }}
          />

          {availableLanguages.length > 0 && (
            <Select
              label={t('localization.selectorLabel')}
              value={language ?? 'default'}
              onChange={(value) => setLanguage(value === 'default' ? null : value)}
              allowDeselect={false}
              data={[
                { value: 'default', label: t('localization.defaultOption') },
                ...availableLanguages.map((code) => ({
                  value: code,
                  label: t(`localization.languageNames.${code}`, {
                    defaultValue: code.toUpperCase(),
                  }),
                })),
              ]}
              w={{ base: '100%', sm: 180 }}
            />
          )}

          {isFetching && !isLoading && (
            <Group gap={6} c="dimmed" pb={6}>
              <Loader size="xs" />
              <Text size="sm">{t('requestsList.refreshing')}</Text>
            </Group>
          )}
        </Group>
      </Stack>

      <Paper withBorder radius="lg" p="md">
        <Stack gap="sm">
          <SimpleGrid cols={{ base: 2, md: 4 }}>
            <Stat label={t('requestsList.stats.total')} value={stats.total} />
            <Stat label={t('requestsList.stats.movies')} value={stats.byType.movie ?? 0} />
            <Stat label={t('requestsList.stats.series')} value={stats.byType.series ?? 0} />
            <Stat label={t('requestsList.stats.completed')} value={stats.byStatus.completed ?? 0} />
          </SimpleGrid>
          <Divider />
          <Group gap="xs">
            {(Object.keys(stats.byStatus) as MediaRequestStatus[]).map((status) => (
              <Group key={status} gap={6}>
                <StatusBadge status={status} size="sm" />
                <Text size="sm" c="dimmed">
                  {stats.byStatus[status]}
                </Text>
              </Group>
            ))}
          </Group>
        </Stack>
      </Paper>

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
