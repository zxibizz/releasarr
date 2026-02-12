import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Center,
  Heading,
  Spinner,
  Stack,
  Text,
  VStack,
} from '@chakra-ui/react';
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { useReleaseOperations } from '@/features/releases/useReleaseOperations';
import { useReleasesByRequestQuery } from '@/hooks/useReleases';
import { fetchRequestsSummary } from '@/services/api';
import type { MediaRequest, Release } from '@/types';
import { getApiErrorInfo } from '@/utils/errors';
import { sortReleasesByStatus } from '@/utils/releaseHelpers';

import ReleaseCard from './components/ReleaseCard';

interface ReleasesListProps {
  requestId: string;
  onPauseRelease?: (_id: string) => void;
  onResumeRelease?: (_id: string) => void;
  onDeleteRelease?: (_id: string) => void;
  onViewFiles?: (release: Release) => void;
  compact?: boolean;
  onReleasesLoaded?: (releases: Release[]) => void;
  hideEmptyState?: boolean;
}

type RequestSummary = Pick<MediaRequest, 'id' | 'title' | 'year' | 'type'>;

const ReleasesList: React.FC<ReleasesListProps> = ({
  requestId,
  onPauseRelease,
  onResumeRelease,
  onDeleteRelease,
  onViewFiles,
  compact = false,
  onReleasesLoaded,
  hideEmptyState = false,
}) => {
  const { data, isLoading, isFetching, error, refetch } = useReleasesByRequestQuery(requestId, {
    enabled: Boolean(requestId),
  });
  const releases = useMemo(() => data ?? [], [data]);
  const [requestSummaries, setRequestSummaries] = useState<Record<string, RequestSummary>>({});
  const { deleteRelease, pauseRelease, resumeRelease } = useReleaseOperations(requestId);

  const releasesToRender = useMemo(() => sortReleasesByStatus(releases), [releases]);

  useEffect(() => {
    if (isLoading || isFetching) {
      return;
    }

    onReleasesLoaded?.(releases);
  }, [isFetching, isLoading, releases, onReleasesLoaded]);

  useEffect(() => {
    if (isLoading || isFetching || releases.length === 0) {
      return;
    }

    const uniqueIds = new Set<string>();
    releases.forEach((release) => {
      release.request_ids.forEach((id) => {
        if (id && id !== requestId) {
          uniqueIds.add(id);
        }
      });
    });

    const missingIds = Array.from(uniqueIds).filter((id) => !requestSummaries[id]);

    if (missingIds.length === 0) {
      return;
    }

    let cancelled = false;

    const loadSummaries = async () => {
      try {
        const summaries = await fetchRequestsSummary(missingIds);
        if (cancelled) {
          return;
        }
        setRequestSummaries((prev) => ({ ...prev, ...summaries }));
      } catch (fetchError) {
        console.error('Failed to fetch request summaries', fetchError);
      }
    };

    loadSummaries();

    return () => {
      cancelled = true;
    };
  }, [isFetching, isLoading, releases, requestId, requestSummaries]);

  const handleDeleteRelease = useCallback(
    (id: string) =>
      deleteRelease(id, {
        onSuccess: () => onDeleteRelease?.(id),
      }),
    [deleteRelease, onDeleteRelease],
  );

  const handlePauseRelease = useCallback(
    (id: string) =>
      pauseRelease(id, {
        onSuccess: () => onPauseRelease?.(id),
      }),
    [onPauseRelease, pauseRelease],
  );

  const handleResumeRelease = useCallback(
    (id: string) =>
      resumeRelease(id, {
        onSuccess: () => onResumeRelease?.(id),
      }),
    [onResumeRelease, resumeRelease],
  );

  const errorInfo = error
    ? getApiErrorInfo(error, {
        title: 'Unable to load releases',
        description: 'We could not retrieve releases for this request.',
      })
    : null;

  const showLoadingState = (isLoading || isFetching) && releases.length === 0;

  if (showLoadingState) {
    return (
      <Center py={10} flexDirection="column" gap={4} color="text.subtle">
        <Spinner size="lg" color="brand.400" />
        <Text>Loading releases...</Text>
      </Center>
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
          <AlertTitle fontSize="lg">{errorInfo.title ?? 'Error loading releases'}</AlertTitle>
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

  if (releases.length === 0) {
    if (hideEmptyState) {
      return null;
    }
    return (
      <VStack
        spacing={3}
        py={16}
        bg="bg.subtle"
        borderRadius="xl"
        borderWidth="1px"
        borderColor="border.muted"
      >
        <Text fontSize="4xl">📦</Text>
        <Heading size="md">No releases found</Heading>
        <Text color="text.subtle" fontSize="sm">
          No releases have been added for this request yet.
        </Text>
      </VStack>
    );
  }

  return (
    <Stack spacing={6}>
      <Stack spacing={compact ? 3 : 4}>
        {releasesToRender.map((release) => (
          <ReleaseCard
            key={release.id}
            release={release}
            onPause={handlePauseRelease}
            onResume={handleResumeRelease}
            onDelete={handleDeleteRelease}
            onViewFiles={onViewFiles}
            compact={compact}
            currentRequestId={requestId}
            requestSummaries={requestSummaries}
          />
        ))}
      </Stack>
    </Stack>
  );
};

export default ReleasesList;
