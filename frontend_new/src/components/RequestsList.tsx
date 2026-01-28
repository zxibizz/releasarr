import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Center,
  Heading,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
  VStack,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import React, { useMemo, useState } from 'react';

import { useRequestsList } from '@/hooks/useRequests';
import type { MediaRequest } from '@/types';

import { RequestCard } from './RequestCard';

type FilterKey = 'all' | 'movies' | 'series' | MediaRequest['status'];

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

export const RequestsList: React.FC = () => {
  const [activeFilter, setActiveFilter] = useState<FilterKey>('all');

  const requestFilters = useMemo(() => {
    switch (activeFilter) {
      case 'movies':
        return { type: 'movie' as const };
      case 'series':
        return { type: 'series' as const };
      case 'all':
        return undefined;
      default:
        return { status: activeFilter };
    }
  }, [activeFilter]);

  const { requests, isLoading, isFetching, error, refetch } = useRequestsList(requestFilters);

  const errorMessage =
    error instanceof Error ? error.message : error ? 'Failed to load requests' : null;

  const showLoadingState = (isLoading || isFetching) && requests.length === 0;

  const handleFilterChange = (filter: FilterKey) => {
    setActiveFilter(filter);
  };

  if (showLoadingState) {
    return (
      <Center py={16} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading requests...</Text>
      </Center>
    );
  }

  if (errorMessage) {
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
          <AlertTitle fontSize="lg">Error loading requests</AlertTitle>
          <AlertDescription>{errorMessage}</AlertDescription>
        </Box>
        <Button variant="outline" colorScheme="blue" size="sm" onClick={() => refetch()}>
          Try Again
        </Button>
      </Alert>
    );
  }

  const activeLabel = filterButtons.find((filter) => filter.key === activeFilter)?.label || 'All';

  return (
    <Stack spacing={{ base: 6, md: 10 }}>
      <Stack spacing={2}>
        <Heading size="2xl">Media Requests</Heading>
        <Text color="text.subtle" fontSize="md">
          Track and manage your media server requests
        </Text>
      </Stack>

      <Box bg="bg.subtle" borderRadius="xl" borderWidth="1px" borderColor="border.muted" p={3}>
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
          {requests.length} {requests.length === 1 ? 'request' : 'requests'}
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
            {activeFilter === 'all'
              ? 'No media requests have been created yet.'
              : `No requests match the "${activeFilter}" filter.`}
          </Text>
        </VStack>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          {requests.map((request) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  );
};
