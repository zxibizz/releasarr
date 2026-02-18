import {
  Button,
  Card,
  Skeleton,
  SkeletonCircle,
  SkeletonText,
  Stack,
  Text,
  useDisclosure,
  useToast,
} from '@chakra-ui/react';
import type { UseToastOptions } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useParams } from 'react-router-dom';

import { RequestActions, type RequestActionItem } from '@/features/requests/components/RequestActions';
import { RequestHeader } from '@/features/requests/components/RequestHeader';
import { RequestLogsModal } from '@/features/requests/components/RequestLogsModal';
import { RequestManualSearchSection } from '@/features/requests/components/RequestManualSearchSection';
import { RequestReleasesSection } from '@/features/requests/components/RequestReleasesSection';
import ReleaseFilesModal from '@/features/requests/ReleaseFilesModal';
import { useRequestLogs } from '@/features/requests/useRequestLogs';
import { useRequestQuery } from '@/hooks/useRequests';
import { releasesKeys } from '@/lib/queryKeys';
import type { Release } from '@/types';
import { getApiErrorInfo } from '@/utils/errors';

const shakeKeyframes = keyframes`
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
`;

const MANUAL_SEARCH_ANIMATION = `${shakeKeyframes} 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97)`;
const MIN_SHAKE_INTERVAL_MS = 1200;

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const {
    data: request,
    isLoading,
    isFetching,
    error: requestError,
    refetch: refetchRequest,
  } = useRequestQuery(id, {
    enabled: Boolean(id),
  });
  const requestId = request?.id;
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);
  const [hasExistingReleases, setHasExistingReleases] = useState(false);
  const [manualSearchTriggered, setManualSearchTriggered] = useState(false);
  const [shakeSignal, setShakeSignal] = useState(0);
  const [isShaking, setIsShaking] = useState(false);
  const [manualSearchPrefill, setManualSearchPrefill] = useState<string | null>(null);
  const [manualSearchFocusToken, setManualSearchFocusToken] = useState(0);
  const [hasLoadedReleases, setHasLoadedReleases] = useState(false);
  const {
    logs: requestLogs,
    isLoading: logsLoading,
    error: logsError,
    loadLogs,
    reset: resetLogs,
  } = useRequestLogs();
  const [expandedStacks, setExpandedStacks] = useState<Record<string, boolean>>({});
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshToastIdRef = useRef<string | number | undefined>(undefined);
  const manualSearchSectionRef = useRef<HTMLDivElement | null>(null);
  const lastShakeAtRef = useRef(0);
  const previousShouldShowSearch = useRef(false);

  const filesModal = useDisclosure();
  const { isOpen: isLogsOpen, onOpen: openLogs, onClose: closeLogs } = useDisclosure();
  const toast = useToast();

  const showLoadingState = (isLoading || isFetching) && !request;
  const requestErrorInfo = requestError
    ? getApiErrorInfo(requestError, {
        title: 'Unable to load this request',
        description: 'We could not retrieve the latest data for this request.',
      })
    : null;

  const logsErrorInfo = logsError
    ? getApiErrorInfo(logsError, {
        title: 'Unable to load logs',
        description: 'We could not retrieve activity logs for this request.',
      })
    : null;

  const updateRefreshToast = useCallback(
    (options: UseToastOptions) => {
      const toastId = refreshToastIdRef.current;
      if (toastId && toast.isActive(toastId)) {
        toast.update(toastId, options);
      } else {
        refreshToastIdRef.current = toast(options);
      }
    },
    [toast],
  );

  const invalidateReleases = useCallback(async () => {
    if (!id) {
      return;
    }

    await Promise.all([
      queryClient.invalidateQueries({ queryKey: releasesKeys.byRequest(id), exact: true }),
      queryClient.invalidateQueries({ queryKey: releasesKeys.list({ requestId: id }) }),
      queryClient.invalidateQueries({ queryKey: releasesKeys.all }),
    ]);
  }, [id, queryClient]);

  const focusManualSearch = useCallback(() => {
    setManualSearchFocusToken((token) => token + 1);
    requestAnimationFrame(() => {
      manualSearchSectionRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  }, []);

  useEffect(() => {
    setHasExistingReleases(false);
    setManualSearchTriggered(false);
    setManualSearchPrefill(null);
    setManualSearchFocusToken(0);
    resetLogs();
    lastShakeAtRef.current = 0;
    setExpandedStacks({});
    setHasLoadedReleases(false);
  }, [requestId, resetLogs]);

  const handleViewFiles = (release: Release) => {
    setSelectedRelease(release);
    filesModal.onOpen();
  };

  const closeModal = () => {
    filesModal.onClose();
    setSelectedRelease(null);
  };

  const handleReleasesLoaded = useCallback(
    (loadedReleases: Release[]) => {
      const hasReleases = loadedReleases.length > 0;
      setHasExistingReleases(hasReleases);
      setHasLoadedReleases(true);

      if (!hasReleases) {
        setManualSearchTriggered(false);
        const normalizedTitle = request?.title?.trim() ?? '';
        setManualSearchPrefill((prev) => {
          if (prev && prev.trim().length > 0) {
            return prev;
          }
          return normalizedTitle || null;
        });
      } else {
        setManualSearchPrefill(null);
      }
    },
    [request?.title],
  );

  const handleManualSearch = useCallback(() => {
    if (!request || !request.title) {
      toast({
        title: 'Manual search unavailable',
        description: 'Missing request details; cannot build search query.',
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    const searchAlreadyVisible = !hasExistingReleases || manualSearchTriggered;
    setManualSearchTriggered(true);
    focusManualSearch();

    if (searchAlreadyVisible) {
      const now = Date.now();
      if (now - lastShakeAtRef.current >= MIN_SHAKE_INTERVAL_MS) {
        lastShakeAtRef.current = now;
        setShakeSignal((signal) => signal + 1);
      }
    } else {
      lastShakeAtRef.current = Date.now();
    }

    const normalizedQuery = request.title.trim();
    if (!normalizedQuery) {
      toast({
        title: 'Manual search unavailable',
        description: 'Request title is empty; please update the request first.',
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    setManualSearchPrefill(normalizedQuery);
  }, [focusManualSearch, hasExistingReleases, manualSearchTriggered, request, toast]);

  const handleRefreshStatus = useCallback(async () => {
    if (!id || isRefreshing) {
      return;
    }

    setIsRefreshing(true);

    const loadingToastId = toast({
      id: `refresh-request-${id}`,
      title: 'Refreshing status',
      description: 'Checking for the latest updates...',
      status: 'info',
      duration: null,
      isClosable: false,
    });
    refreshToastIdRef.current = loadingToastId;

    try {
      await refetchRequest();
      await invalidateReleases();

      updateRefreshToast({
        title: 'Status refreshed',
        description: 'Request details and releases are up to date.',
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to refresh request';
      updateRefreshToast({
        title: 'Refresh failed',
        description: message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setIsRefreshing(false);
      refreshToastIdRef.current = undefined;
    }
  }, [id, invalidateReleases, isRefreshing, refetchRequest, toast, updateRefreshToast]);

  const handleViewLogs = useCallback(() => {
    if (!requestId) {
      return;
    }
    void loadLogs(requestId);
    openLogs();
  }, [loadLogs, openLogs, requestId]);

  useEffect(() => {
    if (shakeSignal === 0) {
      return;
    }
    setIsShaking(true);
    const timeout = window.setTimeout(() => setIsShaking(false), 500);
    return () => window.clearTimeout(timeout);
  }, [shakeSignal]);

  const actionCards: RequestActionItem[] = useMemo(
    () => [
      {
        title: 'Refresh Status',
        description: 'Check for updates on this request',
        icon: '🔄',
        onClick: handleRefreshStatus,
        isLoading: isRefreshing,
        isDisabled: isRefreshing,
        loadingText: 'Refreshing...',
      },
      {
        title: 'Manual Search',
        description: 'Trigger a manual search for releases',
        icon: '🔍',
        onClick: handleManualSearch,
      },
      {
        title: 'View Logs',
        description: 'Check processing logs for this request',
        icon: '📋',
        onClick: handleViewLogs,
      },
    ],
    [handleManualSearch, handleRefreshStatus, handleViewLogs, isRefreshing],
  );

  const shouldShowSearch = !hasExistingReleases || manualSearchTriggered;

  useEffect(() => {
    if (!hasLoadedReleases) {
      return;
    }

    if (shouldShowSearch && !previousShouldShowSearch.current) {
      focusManualSearch();
    }
    previousShouldShowSearch.current = shouldShowSearch;
  }, [focusManualSearch, shouldShowSearch, hasLoadedReleases]);

  if (showLoadingState) {
    return (
      <Stack spacing={8} maxW="6xl" mx="auto">
        <Card p={{ base: 5, md: 6 }}>
          <Stack spacing={4}>
            <Skeleton height="28px" width="240px" borderRadius="md" />
            <SkeletonText noOfLines={3} spacing="2" skeletonHeight="14px" />
            <Stack direction="row" spacing={4} align="center">
              <SkeletonCircle size="12" />
              <Skeleton height="20px" width="160px" borderRadius="full" />
            </Stack>
          </Stack>
        </Card>

        <Card p={{ base: 5, md: 6 }}>
          <Stack spacing={4}>
            <Skeleton height="20px" width="120px" borderRadius="md" />
            <SkeletonText noOfLines={2} spacing="2" skeletonHeight="12px" />
            <Stack spacing={3}>
              {Array.from({ length: 2 }).map((_, index) => (
                <Stack
                  key={`release-skeleton-${index}`}
                  borderWidth="1px"
                  borderRadius="lg"
                  borderColor="border.muted"
                  bg="bg.subtle"
                  p={4}
                  spacing={3}
                >
                  <Skeleton height="18px" width="60%" borderRadius="md" />
                  <SkeletonText noOfLines={2} spacing="2" skeletonHeight="12px" />
                </Stack>
              ))}
            </Stack>
          </Stack>
        </Card>

        <Card p={{ base: 5, md: 6 }}>
          <Stack spacing={4}>
            <Skeleton height="20px" width="140px" borderRadius="md" />
            <Skeleton height="48px" borderRadius="lg" />
            <SkeletonText noOfLines={3} spacing="2" skeletonHeight="12px" />
          </Stack>
        </Card>
      </Stack>
    );
  }

  if (requestErrorInfo || !request) {
    return (
      <Card p={8} maxW="lg" mx="auto">
        <Stack spacing={4} align="center">
          <Text fontSize="3xl">❌</Text>
          <Text as="h2" fontSize="lg" fontWeight="600">
            Request not found
          </Text>
          <Text color="text.subtle" textAlign="center">
            {(requestErrorInfo && requestErrorInfo.description) ||
              'The requested media could not be found.'}
          </Text>
          <Button as={RouterLink} to="/" colorScheme="blue">
            ← Back to Requests
          </Button>
        </Stack>
      </Card>
    );
  }

  return (
    <Stack spacing={8} maxW="6xl" mx="auto">
      <RequestHeader request={request} />

      <RequestReleasesSection
        request={request}
        hasExistingReleases={hasExistingReleases}
        onReleasesLoaded={handleReleasesLoaded}
        onViewFiles={handleViewFiles}
      />

      <RequestManualSearchSection
        request={request}
        shouldShowSearch={shouldShowSearch}
        manualSearchSectionRef={manualSearchSectionRef}
        isShaking={isShaking}
        shakeAnimation={MANUAL_SEARCH_ANIMATION}
        manualSearchPrefill={manualSearchPrefill}
        manualSearchFocusToken={manualSearchFocusToken}
        onDownloadQueued={invalidateReleases}
      />

      <RequestActions actions={actionCards} />

      <ReleaseFilesModal
        isOpen={filesModal.isOpen}
        onClose={closeModal}
        release={selectedRelease}
        currentRequest={request}
      />

      <RequestLogsModal
        isOpen={isLogsOpen}
        onClose={closeLogs}
        logs={requestLogs}
        requestTitle={request.title}
        isLoading={logsLoading}
        error={logsErrorInfo?.description ?? null}
        expandedStacks={expandedStacks}
        setExpandedStacks={setExpandedStacks}
      />
    </Stack>
  );
};
