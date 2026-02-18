import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  HStack,
  Heading,
  Skeleton,
  SkeletonText,
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

  const showInitialLoadingState = (isLoading || isFetching) && releases.length === 0;
  const isBackgroundRefreshing = !showInitialLoadingState && isFetching;

  if (showInitialLoadingState) {
    return (
      <Stack spacing={4}>
        {Array.from({ length: compact ? 2 : 3 }).map((_, index) => (
          <Stack
            key={`release-skeleton-${index}`}
            borderWidth="1px"
            borderColor="border.muted"
            borderRadius="xl"
            bg="bg.subtle"
            p={compact ? 3 : 4}
            spacing={3}
          >
            <Skeleton height="18px" width="40%" borderRadius="md" />
            <SkeletonText noOfLines={compact ? 2 : 3} spacing="2" skeletonHeight="12px" />
            <Skeleton height="32px" width={compact ? '80px' : '120px'} borderRadius="full" />
          </Stack>
        ))}
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
      {isBackgroundRefreshing && (
        <HStack spacing={2} color="text.subtle" fontSize="sm" role="status">
          <Spinner size="sm" />
          <Text>Refreshing releases…</Text>
        </HStack>
      )}
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
