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
import React, {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type SetStateAction,
} from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, useParams } from 'react-router-dom';

import { releasesKeys } from '@/features/releases/queryKeys';
import { RequestActions, type RequestActionItem } from '@/features/requests/components/RequestActions';
import { RequestHeader } from '@/features/requests/components/RequestHeader';
import { RequestLogsModal } from '@/features/requests/components/RequestLogsModal';
import { RequestManualSearchSection } from '@/features/requests/components/RequestManualSearchSection';
import { RequestReleasesSection } from '@/features/requests/components/RequestReleasesSection';
import ReleaseFilesModal from '@/features/requests/ReleaseFilesModal';
import { useRequestLogs } from '@/features/requests/useRequestLogs';
import { useRequestQuery } from '@/hooks/useRequests';
import type { Release } from '@/types';
import { getApiErrorInfo } from '@/utils/errors';

const shakeKeyframes = keyframes`
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
`;

const MANUAL_SEARCH_ANIMATION = `${shakeKeyframes} 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97)`;
const MIN_SHAKE_INTERVAL_MS = 1200;

interface RequestPageState {
  selectedRelease: Release | null;
  hasExistingReleases: boolean;
  manualSearchTriggered: boolean;
  manualSearchPrefill: string | null;
  manualSearchFocusToken: number;
  hasLoadedReleases: boolean;
  shakeTick: number;
  isShaking: boolean;
  expandedStacks: Record<string, boolean>;
  isRefreshing: boolean;
}

type RequestPageAction =
  | { type: 'RESET' }
  | { type: 'SET_SELECTED_RELEASE'; payload: Release | null }
  | { type: 'RELEASES_LOADED'; payload: { releases: Release[]; normalizedTitle: string } }
  | { type: 'TRIGGER_MANUAL_SEARCH'; payload: string }
  | { type: 'SET_MANUAL_SEARCH_TRIGGERED'; payload: boolean }
  | { type: 'INCREMENT_FOCUS_TOKEN' }
  | { type: 'TRIGGER_SHAKE' }
  | { type: 'STOP_SHAKE' }
  | { type: 'SET_EXPANDED_STACKS'; payload: Record<string, boolean> }
  | { type: 'SET_IS_REFRESHING'; payload: boolean };

const initialRequestPageState: RequestPageState = {
  selectedRelease: null,
  hasExistingReleases: false,
  manualSearchTriggered: false,
  manualSearchPrefill: null,
  manualSearchFocusToken: 0,
  hasLoadedReleases: false,
  shakeTick: 0,
  isShaking: false,
  expandedStacks: {},
  isRefreshing: false,
};

function requestPageReducer(state: RequestPageState, action: RequestPageAction): RequestPageState {
  switch (action.type) {
    case 'RESET':
      return { ...initialRequestPageState };
    case 'SET_SELECTED_RELEASE':
      return { ...state, selectedRelease: action.payload };
    case 'RELEASES_LOADED': {
      const { releases, normalizedTitle } = action.payload;
      const hasReleases = releases.length > 0;
      const trimmedPrefill = state.manualSearchPrefill?.trim();
      const manualSearchPrefill = hasReleases
        ? null
        : trimmedPrefill && trimmedPrefill.length > 0
          ? state.manualSearchPrefill
          : normalizedTitle || null;

      return {
        ...state,
        hasExistingReleases: hasReleases,
        hasLoadedReleases: true,
        manualSearchTriggered: hasReleases ? state.manualSearchTriggered : false,
        manualSearchPrefill,
      };
    }
    case 'TRIGGER_MANUAL_SEARCH':
      return {
        ...state,
        manualSearchTriggered: true,
        manualSearchPrefill: action.payload,
      };
    case 'SET_MANUAL_SEARCH_TRIGGERED':
      return { ...state, manualSearchTriggered: action.payload };
    case 'INCREMENT_FOCUS_TOKEN':
      return { ...state, manualSearchFocusToken: state.manualSearchFocusToken + 1 };
    case 'TRIGGER_SHAKE':
      return { ...state, shakeTick: state.shakeTick + 1, isShaking: true };
    case 'STOP_SHAKE':
      return { ...state, isShaking: false };
    case 'SET_EXPANDED_STACKS':
      return { ...state, expandedStacks: action.payload };
    case 'SET_IS_REFRESHING':
      return { ...state, isRefreshing: action.payload };
    default:
      return state;
  }
}

export const RequestPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
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
  const [state, dispatch] = useReducer(requestPageReducer, initialRequestPageState);
  const {
    logs: requestLogs,
    isLoading: logsLoading,
    error: logsError,
    loadLogs,
    reset: resetLogs,
  } = useRequestLogs();
  const {
    selectedRelease,
    hasExistingReleases,
    manualSearchTriggered,
    manualSearchPrefill,
    manualSearchFocusToken,
    hasLoadedReleases,
    isShaking,
    expandedStacks,
    isRefreshing,
    shakeTick,
  } = state;
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
        title: t('requestPage.errors.loadRequestTitle'),
        description: t('requestPage.errors.loadRequestDescription'),
      })
    : null;

  const logsErrorInfo = logsError
    ? getApiErrorInfo(logsError, {
        title: t('requestPage.errors.loadLogsTitle'),
        description: t('requestPage.errors.loadLogsDescription'),
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
    dispatch({ type: 'INCREMENT_FOCUS_TOKEN' });
    requestAnimationFrame(() => {
      manualSearchSectionRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    });
  }, [dispatch]);

  useEffect(() => {
    dispatch({ type: 'RESET' });
    resetLogs();
    lastShakeAtRef.current = 0;
    previousShouldShowSearch.current = false;
  }, [dispatch, requestId, resetLogs]);

  const handleViewFiles = (release: Release) => {
    dispatch({ type: 'SET_SELECTED_RELEASE', payload: release });
    filesModal.onOpen();
  };

  const closeModal = () => {
    filesModal.onClose();
    dispatch({ type: 'SET_SELECTED_RELEASE', payload: null });
  };

  const handleReleasesLoaded = useCallback(
    (loadedReleases: Release[]) => {
      const normalizedTitle = request?.title?.trim() ?? '';
      dispatch({
        type: 'RELEASES_LOADED',
        payload: { releases: loadedReleases, normalizedTitle },
      });
    },
    [dispatch, request?.title],
  );

  const handleManualSearch = useCallback(() => {
    if (!request || !request.title) {
      toast({
        title: t('requestPage.manualSearch.unavailableTitle'),
        description: t('requestPage.manualSearch.missingDetails'),
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    const searchAlreadyVisible = !hasExistingReleases || manualSearchTriggered;
    dispatch({ type: 'SET_MANUAL_SEARCH_TRIGGERED', payload: true });
    focusManualSearch();

    if (searchAlreadyVisible) {
      const now = Date.now();
      if (now - lastShakeAtRef.current >= MIN_SHAKE_INTERVAL_MS) {
        lastShakeAtRef.current = now;
        dispatch({ type: 'TRIGGER_SHAKE' });
      }
    } else {
      lastShakeAtRef.current = Date.now();
    }

    const normalizedQuery = request.title.trim();
    if (!normalizedQuery) {
      toast({
        title: t('requestPage.manualSearch.unavailableTitle'),
        description: t('requestPage.manualSearch.emptyDescription'),
        status: 'warning',
        duration: 4000,
        isClosable: true,
      });
      return;
    }

    dispatch({ type: 'TRIGGER_MANUAL_SEARCH', payload: normalizedQuery });
  }, [
    dispatch,
    focusManualSearch,
    hasExistingReleases,
    manualSearchTriggered,
    request,
    toast,
    t,
  ]);

  const handleRefreshStatus = useCallback(async () => {
    if (!id || isRefreshing) {
      return;
    }

    dispatch({ type: 'SET_IS_REFRESHING', payload: true });

    const loadingToastId = toast({
      id: `refresh-request-${id}`,
      title: t('requestPage.toasts.refreshPendingTitle'),
      description: t('requestPage.toasts.refreshPendingDescription'),
      status: 'info',
      duration: null,
      isClosable: false,
    });
    refreshToastIdRef.current = loadingToastId;

    try {
      await refetchRequest();
      await invalidateReleases();

      updateRefreshToast({
        title: t('requestPage.toasts.refreshSuccessTitle'),
        description: t('requestPage.toasts.refreshSuccessDescription'),
        status: 'success',
        duration: 2500,
        isClosable: true,
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('requestPage.toasts.refreshErrorFallback');
      updateRefreshToast({
        title: t('requestPage.toasts.refreshErrorTitle'),
        description: message,
        status: 'error',
        duration: 4000,
        isClosable: true,
      });
    } finally {
      dispatch({ type: 'SET_IS_REFRESHING', payload: false });
      refreshToastIdRef.current = undefined;
    }
  }, [
    dispatch,
    id,
    invalidateReleases,
    isRefreshing,
    refetchRequest,
    toast,
    updateRefreshToast,
    t,
  ]);

  const handleViewLogs = useCallback(() => {
    if (!requestId) {
      return;
    }
    void loadLogs(requestId);
    openLogs();
  }, [loadLogs, openLogs, requestId]);

  const handleSetExpandedStacks = useCallback(
    (updater: SetStateAction<Record<string, boolean>>) => {
      const nextValue =
        typeof updater === 'function' ? (updater as (prev: Record<string, boolean>) => Record<string, boolean>)(expandedStacks) : updater;
      dispatch({ type: 'SET_EXPANDED_STACKS', payload: nextValue });
    },
    [dispatch, expandedStacks],
  );

  useEffect(() => {
    if (shakeTick === 0) {
      return;
    }
    const timeout = window.setTimeout(() => dispatch({ type: 'STOP_SHAKE' }), 500);
    return () => window.clearTimeout(timeout);
  }, [dispatch, shakeTick]);

  const actionCards: RequestActionItem[] = useMemo(
    () => [
      {
        title: t('requestPage.actions.refresh.title'),
        description: t('requestPage.actions.refresh.description'),
        icon: '🔄',
        onClick: handleRefreshStatus,
        isLoading: isRefreshing,
        isDisabled: isRefreshing,
        loadingText: t('requestPage.actions.refresh.loadingText'),
      },
      {
        title: t('requestPage.actions.manualSearch.title'),
        description: t('requestPage.actions.manualSearch.description'),
        icon: '🔍',
        onClick: handleManualSearch,
      },
      {
        title: t('requestPage.actions.logs.title'),
        description: t('requestPage.actions.logs.description'),
        icon: '📋',
        onClick: handleViewLogs,
      },
    ],
    [handleManualSearch, handleRefreshStatus, handleViewLogs, isRefreshing, t],
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
            {t('requestPage.errors.notFoundTitle')}
          </Text>
          <Text color="text.subtle" textAlign="center">
            {(requestErrorInfo && requestErrorInfo.description) ||
              t('requestPage.errors.notFoundDescription')}
          </Text>
          <Button as={RouterLink} to="/" colorScheme="blue">
            {t('common.backToRequests')}
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
        setExpandedStacks={handleSetExpandedStacks}
      />
    </Stack>
  );
};
