import { Alert, Button, Group, Loader, Paper, Skeleton, Stack, Text, Title } from '@mantine/core';
import { useEffect, useMemo, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { ReleaseCard } from '@/features/releases/components/ReleaseCard';
import { useReleaseActions, useReleasesByRequest } from '@/features/releases/queries';
import { useRequestsList } from '@/features/requests/queries';
import type { Release } from '@/types';
import { getErrorMessage } from '@/utils/errors';

const STATUS_ORDER = ['downloading', 'pending', 'seeding', 'completed', 'failed'];

const sortReleases = (releases: Release[]): Release[] =>
  [...releases].sort((a, b) => {
    const byStatus = STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status);
    if (byStatus !== 0) {
      return byStatus;
    }
    return new Date(b.added_date).getTime() - new Date(a.added_date).getTime();
  });

interface ReleaseListProps {
  requestId: string;
  onViewFiles: (release: Release) => void;
  onReleasesLoaded?: (releases: Release[]) => void;
}

export function ReleaseList({ requestId, onViewFiles, onReleasesLoaded }: ReleaseListProps) {
  const { t } = useTranslation();
  const { data, isLoading, isFetching, error, refetch } = useReleasesByRequest(requestId);
  const { pause, resume, remove } = useReleaseActions(requestId);

  // The requests list is already cached by the home route loader, so related
  // request titles come for free instead of a per-release lookup.
  const { requests } = useRequestsList();
  const relatedRequestTitles = useMemo(
    () => new Map(requests.map((request) => [request.id, request.title])),
    [requests],
  );

  const releases = useMemo(() => sortReleases(data ?? []), [data]);
  const isBusy = pause.isPending || resume.isPending || remove.isPending;

  useEffect(() => {
    if (!isLoading && !isFetching) {
      onReleasesLoaded?.(releases);
    }
  }, [isLoading, isFetching, releases, onReleasesLoaded]);

  const section = (children: ReactNode) => (
    <Stack gap="md">
      <Title order={3}>{t('releasesList.title')}</Title>
      {children}
    </Stack>
  );

  if (isLoading && releases.length === 0) {
    return section(
      <Stack gap="md">
        {Array.from({ length: 2 }).map((_, index) => (
          <Paper key={index} withBorder radius="lg" p="lg">
            <Stack gap="sm">
              <Skeleton height={18} width="40%" />
              <Skeleton height={12} />
              <Skeleton height={12} width="70%" />
            </Stack>
          </Paper>
        ))}
      </Stack>,
    );
  }

  if (error) {
    return section(
      <Alert color="red" radius="lg" title={t('releasesList.error.title')}>
        <Stack align="flex-start" gap="sm">
          <Text>{getErrorMessage(error, t('releasesList.error.description'))}</Text>
          <Button size="xs" variant="light" onClick={() => void refetch()}>
            {t('common.tryAgain')}
          </Button>
        </Stack>
      </Alert>,
    );
  }

  // Nothing to announce when a request has no releases yet — the manual search
  // panel below takes over as the call to action.
  if (releases.length === 0) {
    return null;
  }

  return section(
    <Stack gap="md">
      {isFetching && (
        <Group gap={6} c="dimmed">
          <Loader size="xs" />
          <Text size="sm">{t('releasesList.refreshing')}</Text>
        </Group>
      )}

      {releases.map((release) => (
        <ReleaseCard
          key={release.id}
          release={release}
          currentRequestId={requestId}
          relatedRequestTitles={relatedRequestTitles}
          onViewFiles={onViewFiles}
          onPause={(id) => pause.mutate(id)}
          onResume={(id) => resume.mutate(id)}
          onDelete={(id) => remove.mutate(id)}
          isBusy={isBusy}
        />
      ))}
    </Stack>,
  );
}
