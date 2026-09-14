import { Button, Card, Skeleton, Stack, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { LogsModal } from '@/features/logs/LogsModal';
import { ReleaseFilesModal } from '@/features/releases/components/ReleaseFilesModal';
import { ReleaseList } from '@/features/releases/components/ReleaseList';
import { ReleaseSearch } from '@/features/releases/components/ReleaseSearch';
import { releaseKeys } from '@/features/releases/queries';
import { ManageSeasonsModal } from '@/features/requests/components/ManageSeasonsModal';
import { MediaInfo } from '@/features/requests/components/MediaInfo';
import { RequestActions } from '@/features/requests/components/RequestActions';
import { RequestOwner } from '@/features/requests/components/RequestOwner';
import { SeasonEpisodes } from '@/features/requests/components/SeasonEpisodes';
import {
  localizeRequest,
  useMetadataLanguage,
  useRequestTitles,
} from '@/features/requests/localization';
import { requestKeys, useRemoveRequest, useRequest } from '@/features/requests/queries';
import type { Release } from '@/types';

function DetailSkeleton() {
  return (
    <Stack gap="xl">
      <Card withBorder radius="lg" padding="lg">
        <Stack gap="md">
          <Skeleton height={28} width={240} />
          <Skeleton height={12} />
          <Skeleton height={12} width="70%" />
        </Stack>
      </Card>
      <Skeleton height={160} radius="lg" />
    </Stack>
  );
}

export function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: request, isLoading, error } = useRequest(id);
  const removeRequest = useRemoveRequest();

  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);
  const [hasReleases, setHasReleases] = useState(false);
  const [searchRequested, setSearchRequested] = useState(false);
  const [focusToken, setFocusToken] = useState(0);

  const [filesOpened, filesModal] = useDisclosure(false);
  const [logsOpened, logsModal] = useDisclosure(false);
  const [seasonsOpened, seasonsModal] = useDisclosure(false);
  const [isRefreshing, setRefreshing] = useState(false);

  const searchSectionRef = useRef<HTMLDivElement>(null);

  const metadataLanguage = useMetadataLanguage();
  const titleOptions = useRequestTitles(request);

  const localizedRequest = useMemo(
    () => (request ? localizeRequest(request, metadataLanguage) : null),
    [request, metadataLanguage],
  );

  const handleReleasesLoaded = useCallback((releases: Release[]) => {
    setHasReleases(releases.length > 0);
  }, []);

  const invalidateReleases = useCallback(() => {
    if (id) {
      void queryClient.invalidateQueries({ queryKey: releaseKeys.byRequest(id) });
    }
  }, [id, queryClient]);

  const handleRefresh = useCallback(async () => {
    if (!id) return;
    setRefreshing(true);
    try {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: requestKeys.detail(id) }),
        // An import that landed since the page opened shows up as episodes
        // gained rather than anything the request row itself says.
        queryClient.invalidateQueries({ queryKey: requestKeys.episodes(id) }),
        queryClient.invalidateQueries({ queryKey: releaseKeys.byRequest(id) }),
      ]);
      notifications.show({
        title: t('requestPage.toasts.refreshSuccessTitle'),
        message: t('requestPage.toasts.refreshSuccessDescription'),
        color: 'teal',
      });
    } finally {
      setRefreshing(false);
    }
  }, [id, queryClient, t]);

  const handleManualSearch = useCallback(() => {
    setSearchRequested(true);
    setFocusToken((token) => token + 1);
    requestAnimationFrame(() => {
      searchSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }, []);

  const handleViewFiles = useCallback(
    (release: Release) => {
      setSelectedRelease(release);
      filesModal.open();
    },
    [filesModal],
  );

  const backToRequests = useCallback(() => void navigate('/'), [navigate]);

  const confirmRemove = useCallback(() => {
    if (!request) return;
    modals.openConfirmModal({
      title: t('requestPage.remove.dialogTitle'),
      children: (
        <Text size="sm">
          {t(
            request.type === 'movie'
              ? 'requestPage.remove.dialogBodyMovie'
              : 'requestPage.remove.dialogBodySeries',
          )}
        </Text>
      ),
      labels: { confirm: t('requestPage.remove.confirm'), cancel: t('common.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => removeRequest.mutate(request.id, { onSuccess: backToRequests }),
    });
  }, [backToRequests, removeRequest, request, t]);

  if (isLoading && !request) {
    return <DetailSkeleton />;
  }

  if (error || !localizedRequest) {
    return (
      <EmptyState
        icon="❌"
        title={t('requestPage.errors.notFoundTitle')}
        description={t('requestPage.errors.notFoundDescription')}
        action={
          <Button component={Link} to="/" mt="sm">
            {t('common.backToRequests')}
          </Button>
        }
      />
    );
  }

  const showSearch = !hasReleases || searchRequested;

  return (
    <Stack gap="xl">
      <MediaInfo
        request={localizedRequest}
        onManageSeasons={localizedRequest.type === 'series' ? seasonsModal.open : undefined}
      />

      <RequestOwner request={localizedRequest} />

      {localizedRequest.type === 'series' && <SeasonEpisodes requestId={localizedRequest.id} />}

      <ReleaseList
        requestId={localizedRequest.id}
        onViewFiles={handleViewFiles}
        onReleasesLoaded={handleReleasesLoaded}
      />

      <div ref={searchSectionRef}>
        {showSearch && (
          <ReleaseSearch
            requestId={localizedRequest.id}
            requestTitle={localizedRequest.title}
            prefillQuery={localizedRequest.title}
            titleOptions={titleOptions}
            seasonNumber={
              localizedRequest.type === 'series' ? localizedRequest.season_number : undefined
            }
            focusToken={focusToken}
            onDownloadQueued={invalidateReleases}
          />
        )}
      </div>

      <RequestActions
        actions={[
          {
            key: 'refresh',
            icon: '🔄',
            title: t('requestPage.actions.refresh.title'),
            description: t('requestPage.actions.refresh.description'),
            onClick: () => void handleRefresh(),
            loading: isRefreshing,
          },
          {
            key: 'search',
            icon: '🔍',
            title: t('requestPage.actions.manualSearch.title'),
            description: t('requestPage.actions.manualSearch.description'),
            onClick: handleManualSearch,
          },
          {
            key: 'logs',
            icon: '📋',
            title: t('requestPage.actions.logs.title'),
            description: t('requestPage.actions.logs.description'),
            onClick: logsModal.open,
          },
          {
            key: 'remove',
            icon: '🗑️',
            title: t('requestPage.actions.remove.title'),
            description: t('requestPage.actions.remove.description'),
            onClick: confirmRemove,
            loading: removeRequest.isPending,
            danger: true,
          },
        ]}
      />

      <ReleaseFilesModal
        release={selectedRelease}
        currentRequest={localizedRequest}
        opened={filesOpened}
        onClose={filesModal.close}
      />

      <LogsModal
        requestId={localizedRequest.id}
        requestTitle={localizedRequest.title}
        opened={logsOpened}
        onClose={logsModal.close}
      />

      {localizedRequest.type === 'series' && (
        <ManageSeasonsModal
          request={localizedRequest}
          opened={seasonsOpened}
          onClose={seasonsModal.close}
          onRequestRemoved={backToRequests}
        />
      )}
    </Stack>
  );
}
