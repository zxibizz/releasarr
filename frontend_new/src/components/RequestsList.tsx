import { SearchIcon } from '@chakra-ui/icons';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  Divider,
  Flex,
  Heading,
  HStack,
  Icon,
  Input,
  InputGroup,
  InputLeftElement,
  Select,
  SimpleGrid,
  Skeleton,
  SkeletonText,
  Spinner,
  Stack,
  Stat,
  StatLabel,
  StatNumber,
  Text,
  VStack,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { useRequestsList } from '@/hooks/useRequests';
import type { MediaRequest } from '@/types';
import { getApiErrorInfo } from '@/utils/errors';

import { RequestCard } from './RequestCard';

type FilterKey = 'all' | 'movies' | 'series' | MediaRequest['status'];
type SortKey = 'created_desc' | 'created_asc' | 'title_asc' | 'title_desc';

const FILTER_KEYS: readonly FilterKey[] = [
  'all',
  'movies',
  'series',
  'pending',
  'searching',
  'downloading',
  'completed',
  'failed',
] as const;

const SORT_KEYS: readonly SortKey[] = ['created_desc', 'created_asc', 'title_asc', 'title_desc'] as const;

const FILTER_CONFIGS: ReadonlyArray<{ key: FilterKey; labelKey: string }> = [
  { key: 'all', labelKey: 'requestsList.filters.all' },
  { key: 'movies', labelKey: 'requestsList.filters.movies' },
  { key: 'series', labelKey: 'requestsList.filters.series' },
  { key: 'pending', labelKey: 'status.pending' },
  { key: 'searching', labelKey: 'status.searching' },
  { key: 'downloading', labelKey: 'status.downloading' },
  { key: 'completed', labelKey: 'status.completed' },
  { key: 'failed', labelKey: 'status.failed' },
];

const SORT_CONFIGS: ReadonlyArray<{ key: SortKey; labelKey: string }> = [
  { key: 'created_desc', labelKey: 'requestsList.sort.created_desc' },
  { key: 'created_asc', labelKey: 'requestsList.sort.created_asc' },
  { key: 'title_asc', labelKey: 'requestsList.sort.title_asc' },
  { key: 'title_desc', labelKey: 'requestsList.sort.title_desc' },
];

const DEFAULT_FILTER: FilterKey = 'all';
const DEFAULT_SORT: SortKey = 'created_desc';

const isValidFilter = (value: string | null): value is FilterKey =>
  Boolean(value && FILTER_KEYS.includes(value as FilterKey));

const isValidSort = (value: string | null): value is SortKey =>
  Boolean(value && SORT_KEYS.includes(value as SortKey));

const normalizeText = (value: string | null | undefined) => value?.trim().toLowerCase() ?? '';

export const RequestsList: React.FC = () => {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeFilterParam = searchParams.get('filter');
  const sortParam = searchParams.get('sort');
  const queryParam = searchParams.get('q');

  const activeFilter = isValidFilter(activeFilterParam) ? activeFilterParam : DEFAULT_FILTER;
  const activeSort = isValidSort(sortParam) ? sortParam : DEFAULT_SORT;

  const [searchValue, setSearchValue] = useState(queryParam ?? '');

  useEffect(() => {
    setSearchValue(queryParam ?? '');
  }, [queryParam]);

  const { requests, isLoading, isFetching, error, refetch } = useRequestsList();

  const filterButtons = useMemo(
    () => FILTER_CONFIGS.map((config) => ({ ...config, label: t(config.labelKey) })),
    [t],
  );

  const sortOptions = useMemo(
    () => SORT_CONFIGS.map((config) => ({ ...config, label: t(config.labelKey) })),
    [t],
  );

  const errorInfo = error
    ? getApiErrorInfo(error, {
        title: t('requestsList.error.title'),
        description: t('requestsList.error.description'),
      })
    : null;

  const showInitialLoadingState = isLoading && requests.length === 0;

  const updateParams = (updates: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '') {
        next.delete(key);
      } else {
        next.set(key, value);
      }
    });
    setSearchParams(next, { replace: true });
  };

  const handleFilterChange = (filter: FilterKey) => {
    updateParams({ filter: filter === DEFAULT_FILTER ? null : filter });
  };

  const handleSortChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    updateParams({ sort: value === DEFAULT_SORT ? null : value });
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchValue(value);
    updateParams({ q: value.trim().length === 0 ? null : value });
  };

  const normalizedSearch = normalizeText(searchValue);

  const filteredRequests = useMemo(() => {
    let working = [...requests];

    if (activeFilter === 'movies') {
      working = working.filter((request) => request.type === 'movie');
    } else if (activeFilter === 'series') {
      working = working.filter((request) => request.type === 'series');
    } else if (activeFilter !== 'all') {
      working = working.filter((request) => request.status === activeFilter);
    }

    if (normalizedSearch.length > 0) {
      working = working.filter((request) => {
        const candidates = [
          request.title,
          'series_title' in request ? request.series_title : undefined,
        ];
        return candidates
          .filter((value): value is string => Boolean(value && value.trim().length > 0))
          .some((value) => value.toLowerCase().includes(normalizedSearch));
      });
    }

    const byCreatedDesc = (a: MediaRequest, b: MediaRequest) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    const byCreatedAsc = (a: MediaRequest, b: MediaRequest) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    const byTitleAsc = (a: MediaRequest, b: MediaRequest) => a.title.localeCompare(b.title);
    const byTitleDesc = (a: MediaRequest, b: MediaRequest) => b.title.localeCompare(a.title);

    const sorters: Record<SortKey, (a: MediaRequest, b: MediaRequest) => number> = {
      created_desc: byCreatedDesc,
      created_asc: byCreatedAsc,
      title_asc: byTitleAsc,
      title_desc: byTitleDesc,
    };

    return working.sort(sorters[activeSort]);
  }, [activeFilter, activeSort, normalizedSearch, requests]);

  const stats = useMemo(() => {
    return requests.reduce(
      (acc, request) => {
        acc.total += 1;
        acc.byType[request.type] = (acc.byType[request.type] ?? 0) + 1;
        acc.byStatus[request.status] = (acc.byStatus[request.status] ?? 0) + 1;
        return acc;
      },
      {
        total: 0,
        byType: {} as Record<MediaRequest['type'], number>,
        byStatus: {} as Record<MediaRequest['status'], number>,
      },
    );
  }, [requests]);

  const activeLabel = filterButtons.find((filter) => filter.key === activeFilter)?.label || 'All';

  if (showInitialLoadingState) {
    return (
      <Stack spacing={{ base: 6, md: 10 }}>
        <Skeleton height="32px" width="240px" borderRadius="md" />
        <Stack spacing={6}>
          <Skeleton height="64px" borderRadius="lg" />
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            {Array.from({ length: 4 }).map((_, index) => (
              <Stack
                key={`request-skeleton-${index}`}
                borderWidth="1px"
                borderRadius="xl"
                borderColor="border.muted"
                bg="bg.subtle"
                p={4}
                spacing={3}
              >
                <Skeleton height="20px" width="60%" borderRadius="md" />
                <SkeletonText noOfLines={3} spacing="3" skeletonHeight="12px" />
                <Skeleton height="32px" width="120px" borderRadius="full" />
              </Stack>
            ))}
          </SimpleGrid>
        </Stack>
      </Stack>
    );
  }

  if (errorInfo) {
    return (
      <Alert
        status="error"
        variant="subtle"
        borderRadius="xl"
        p={6}
        flexDirection="column"
        alignItems="flex-start"
        gap={4}
      >
        <AlertIcon />
        <Box>
          <AlertTitle fontSize="lg">
            {errorInfo.title ?? t('requestsList.error.fallbackTitle')}
          </AlertTitle>
          <AlertDescription>
            {errorInfo.description}
            {errorInfo.details && (
              <Text mt={2} fontSize="xs" color="text.subtle" whiteSpace="pre-wrap">
                {errorInfo.details}
              </Text>
            )}
          </AlertDescription>
        </Box>
        <Button variant="outline" colorScheme="blue" size="sm" onClick={() => refetch()}>
          {t('common.tryAgain')}
        </Button>
      </Alert>
    );
  }

  return (
    <Stack spacing={{ base: 6, md: 10 }}>
      <Stack spacing={2}>
        <Heading size="2xl">{t('requestsList.title')}</Heading>
        <Text color="text.subtle" fontSize="md">
          {t('requestsList.subtitle')}
        </Text>
      </Stack>

      <Stack spacing={4}>
        <Wrap spacing={2}>
          {filterButtons.map((filter) => {
            const isActive = activeFilter === filter.key;
            return (
              <WrapItem key={filter.key}>
                <Button
                  size="sm"
                  colorScheme="blue"
                  variant={isActive ? 'solid' : 'outline'}
                  onClick={() => handleFilterChange(filter.key)}
                >
                  {filter.label}
                </Button>
              </WrapItem>
            );
          })}
        </Wrap>

        <Flex
          direction={{ base: 'column', md: 'row' }}
          gap={3}
          align={{ base: 'stretch', md: 'center' }}
        >
          <InputGroup maxW={{ base: 'full', md: '300px' }}>
            <InputLeftElement pointerEvents="none">
              <Icon as={SearchIcon} color="text.subtle" />
            </InputLeftElement>
            <Input
              value={searchValue}
              onChange={handleSearchChange}
              placeholder={t('requestsList.searchPlaceholder')}
              variant="filled"
              bg="bg.subtle"
              _focus={{ bg: 'bg.muted' }}
            />
          </InputGroup>

          <Select
            value={activeSort}
            onChange={handleSortChange}
            maxW={{ base: 'full', md: '220px' }}
            aria-label={t('requestsList.sortAriaLabel')}
          >
            {sortOptions.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </Select>

          {isFetching && !isLoading && (
            <HStack spacing={2} color="text.subtle">
              <Spinner size="sm" />
              <Text fontSize="sm">{t('requestsList.refreshing')}</Text>
            </HStack>
          )}
        </Flex>
      </Stack>

      <Box borderWidth="1px" borderRadius="xl" borderColor="border.muted" bg="bg.subtle" p={4}>
        <Stack spacing={3}>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel>{t('requestsList.stats.total')}</StatLabel>
              <StatNumber>{stats.total}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>{t('requestsList.stats.movies')}</StatLabel>
              <StatNumber>{stats.byType.movie ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>{t('requestsList.stats.series')}</StatLabel>
              <StatNumber>{stats.byType.series ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>{t('requestsList.stats.completed')}</StatLabel>
              <StatNumber>{stats.byStatus.completed ?? 0}</StatNumber>
            </Stat>
          </SimpleGrid>
          <Divider borderColor="border.muted" />
          <Wrap spacing={2} align="center">
            {(Object.keys(stats.byStatus) as MediaRequest['status'][]).map((status) => (
              <Badge
                key={status}
                colorScheme="blue"
                variant="subtle"
                borderRadius="full"
                px={3}
                py={1}
              >
                {t(`status.${status}`)}: {stats.byStatus[status]}
              </Badge>
            ))}
          </Wrap>
        </Stack>
      </Box>

      <Stack
        direction={{ base: 'column', md: 'row' }}
        justify="space-between"
        align={{ base: 'flex-start', md: 'center' }}
        spacing={4}
      >
        <Heading size="md" color="slate.100">
          {activeFilter === 'all'
            ? t('requestsList.headings.all')
            : t('requestsList.headings.filtered', { label: activeLabel })}
        </Heading>
        <Text color="text.subtle" fontSize="sm">
          {t('requestsList.resultsCount', { count: filteredRequests.length })}
        </Text>
      </Stack>

      {requests.length === 0 ? (
        <VStack
          spacing={3}
          py={16}
          bg="bg.subtle"
          borderRadius="xl"
          borderWidth="1px"
          borderColor="border.muted"
        >
          <Text fontSize="4xl">📺</Text>
          <Heading size="md">{t('requestsList.empty.title')}</Heading>
          <Text color="text.subtle" fontSize="sm" textAlign="center">
            {t('requestsList.empty.description')}
          </Text>
        </VStack>
      ) : filteredRequests.length === 0 ? (
        <VStack
          spacing={3}
          py={16}
          bg="bg.subtle"
          borderRadius="xl"
          borderWidth="1px"
          borderColor="border.muted"
        >
          <Text fontSize="4xl">🧭</Text>
          <Heading size="md">{t('requestsList.emptyFiltered.title')}</Heading>
          <Text color="text.subtle" fontSize="sm" textAlign="center">
            {t('requestsList.emptyFiltered.description')}
          </Text>
        </VStack>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          {filteredRequests.map((request) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
};
