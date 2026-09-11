import { Button, Card, Select, Skeleton, Stack } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';
import { LogsModal } from '@/features/logs/LogsModal';
import { ReleaseFilesModal } from '@/features/releases/components/ReleaseFilesModal';
import { ReleaseList } from '@/features/releases/components/ReleaseList';
import { ReleaseSearch } from '@/features/releases/components/ReleaseSearch';
import { releaseKeys } from '@/features/releases/queries';
import { MediaInfo } from '@/features/requests/components/MediaInfo';
import { RequestActions } from '@/features/requests/components/RequestActions';
import { localizeRequest } from '@/features/requests/localization';
import { requestKeys, useRequest } from '@/features/requests/queries';
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

  const { data: request, isLoading, error } = useRequest(id);

  const [language, setLanguage] = useState<string | null>(null);
  const [selectedRelease, setSelectedRelease] = useState<Release | null>(null);
  const [hasReleases, setHasReleases] = useState(false);
  const [searchRequested, setSearchRequested] = useState(false);
  const [focusToken, setFocusToken] = useState(0);

  const [filesOpened, filesModal] = useDisclosure(false);
  const [logsOpened, logsModal] = useDisclosure(false);
  const [isRefreshing, setRefreshing] = useState(false);

  const searchSectionRef = useRef<HTMLDivElement>(null);

  const availableLanguages = useMemo(
    () => Object.keys(request?.localizations ?? {}).sort(),
    [request],
  );

  const activeLanguage =
    language && availableLanguages.includes(language)
      ? language
      : (['rus', 'eng'].find((code) => availableLanguages.includes(code)) ??
        availableLanguages[0] ??
        null);

  const localizedRequest = useMemo(
    () => (request ? localizeRequest(request, activeLanguage) : null),
    [request, activeLanguage],
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
        languageSelector={
          availableLanguages.length > 0 ? (
            <Select
              size="xs"
              w={140}
              aria-label={t('localization.selectorLabel')}
              value={activeLanguage ?? 'default'}
              allowDeselect={false}
              onChange={(value) => setLanguage(value === 'default' ? null : value)}
              data={[
                { value: 'default', label: t('localization.defaultOption') },
                ...availableLanguages.map((code) => ({
                  value: code,
                  label: t(`localization.languageNames.${code}`, {
                    defaultValue: code.toUpperCase(),
                  }),
                })),
              ]}
            />
          ) : null
        }
      />

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
    </Stack>
  );
}
