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
import { useSearchParams } from 'react-router-dom';

import { useRequestsList } from '@/hooks/useRequests';
import type { MediaRequest } from '@/types';
import { getApiErrorInfo } from '@/utils/errors';

import { RequestCard } from './RequestCard';

type FilterKey = 'all' | 'movies' | 'series' | MediaRequest['status'];
type SortKey = 'created_desc' | 'created_asc' | 'title_asc' | 'title_desc';

const filterButtons: ReadonlyArray<{ key: FilterKey; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'movies', label: 'Movies' },
  { key: 'series', label: 'Series' },
  { key: 'pending', label: 'Pending' },
  { key: 'searching', label: 'Searching' },
  { key: 'downloading', label: 'Downloading' },
  { key: 'completed', label: 'Completed' },
  { key: 'failed', label: 'Failed' },
];

const sortOptions: ReadonlyArray<{ key: SortKey; label: string }> = [
  { key: 'created_desc', label: 'Newest first' },
  { key: 'created_asc', label: 'Oldest first' },
  { key: 'title_asc', label: 'Title A → Z' },
  { key: 'title_desc', label: 'Title Z → A' },
];

const DEFAULT_FILTER: FilterKey = 'all';
const DEFAULT_SORT: SortKey = 'created_desc';

const isValidFilter = (value: string | null): value is FilterKey =>
  Boolean(value && filterButtons.some((filter) => filter.key === value));

const isValidSort = (value: string | null): value is SortKey =>
  Boolean(value && sortOptions.some((option) => option.key === value));

const normalizeText = (value: string | null | undefined) => value?.trim().toLowerCase() ?? '';

export const RequestsList: React.FC = () => {
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

  const errorInfo = error
    ? getApiErrorInfo(error, {
        title: 'Unable to load requests',
        description: 'We could not retrieve the latest requests from the server.',
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
          <AlertTitle fontSize="lg">{errorInfo.title ?? 'Error loading requests'}</AlertTitle>
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
          Try Again
        </Button>
      </Alert>
    );
  }

  return (
    <Stack spacing={{ base: 6, md: 10 }}>
      <Stack spacing={2}>
        <Heading size="2xl">Media Requests</Heading>
        <Text color="text.subtle" fontSize="md">
          Track and manage your media server requests
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
              placeholder="Search requests..."
              variant="filled"
              bg="bg.subtle"
              _focus={{ bg: 'bg.muted' }}
            />
          </InputGroup>

          <Select
            value={activeSort}
            onChange={handleSortChange}
            maxW={{ base: 'full', md: '220px' }}
            aria-label="Sort requests"
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
              <Text fontSize="sm">Refreshing data…</Text>
            </HStack>
          )}
        </Flex>
      </Stack>

      <Box borderWidth="1px" borderRadius="xl" borderColor="border.muted" bg="bg.subtle" p={4}>
        <Stack spacing={3}>
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
            <Stat>
              <StatLabel>Total Requests</StatLabel>
              <StatNumber>{stats.total}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Movies</StatLabel>
              <StatNumber>{stats.byType.movie ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Series</StatLabel>
              <StatNumber>{stats.byType.series ?? 0}</StatNumber>
            </Stat>
            <Stat>
              <StatLabel>Completed</StatLabel>
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
                {status.charAt(0).toUpperCase() + status.slice(1)}: {stats.byStatus[status]}
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
          {activeFilter === 'all' ? 'All Requests' : `${activeLabel} Requests`}
        </Heading>
        <Text color="text.subtle" fontSize="sm">
          {filteredRequests.length} {filteredRequests.length === 1 ? 'request' : 'requests'}
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
          <Heading size="md">No requests found</Heading>
          <Text color="text.subtle" fontSize="sm" textAlign="center">
            No media requests have been created yet.
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
          <Heading size="md">No matching requests</Heading>
          <Text color="text.subtle" fontSize="sm" textAlign="center">
            Try adjusting your filters or search query to find more results.
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
