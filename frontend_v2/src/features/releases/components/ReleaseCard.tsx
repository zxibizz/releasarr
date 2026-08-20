import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Progress,
  Stack,
  Text,
  Tooltip,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconTrash } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { StatusBadge } from '@/components/StatusBadge';
import type { Release } from '@/types';
import {
  calculateEta,
  formatDateTime,
  formatFileSize,
  formatProgress,
  formatRatio,
  formatSpeed,
} from '@/utils/formatters';
import { groupFilesByType } from '@/utils/files';

interface ReleaseCardProps {
  release: Release;
  /** Titles of other requests this release also belongs to, keyed by request id. */
  relatedRequestTitles: Map<string, string>;
  currentRequestId: string;
  onViewFiles: (release: Release) => void;
  onPause: (releaseId: string) => void;
  onResume: (releaseId: string) => void;
  onDelete: (releaseId: string) => void;
  isBusy?: boolean;
}

const healthScore = (release: Release): number => {
  if (release.seeders === 0) return 0;
  if (release.leechers === 0) return 100;
  return Math.round((release.seeders / (release.seeders + release.leechers)) * 100);
};

const healthColor = (score: number): string => {
  if (score >= 70) return 'teal';
  if (score >= 40) return 'yellow';
  return 'red';
};

export function ReleaseCard({
  release,
  relatedRequestTitles,
  currentRequestId,
  onViewFiles,
  onPause,
  onResume,
  onDelete,
  isBusy = false,
}: ReleaseCardProps) {
  const { t } = useTranslation();

  const isActive = release.status === 'downloading' || release.status === 'pending';
  const isComplete = release.status === 'completed' || release.status === 'seeding';
  const progress = isComplete ? 100 : release.progress;
  const downloadedBytes = Math.round((progress / 100) * release.size);
  const eta =
    release.status === 'downloading'
      ? calculateEta(release.size, downloadedBytes, release.download_speed)
      : null;

  const files = groupFilesByType(release.files ?? []);
  const health = healthScore(release);

  const relatedRequests = [...new Set(release.request_ids ?? [])].filter(
    (id) => id !== currentRequestId,
  );

  const confirmDelete = () =>
    modals.openConfirmModal({
      title: t('releaseCard.dialog.title'),
      children: <Text size="sm">{t('releaseCard.dialog.body')}</Text>,
      labels: { confirm: t('releaseCard.dialog.confirm'), cancel: t('common.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => onDelete(release.id),
    });

  return (
    <Card withBorder radius="lg" padding="lg">
      <Stack gap="md">
        <Group justify="space-between" align="flex-start" wrap="nowrap" gap="md">
          <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
            <Text fw={700} lineClamp={2}>
              {release.name}
            </Text>
            {release.torrent_source && (
              <Text size="sm" c="dimmed">
                {t('releaseCard.source', { defaultValue: 'Source' })}: {release.torrent_source}
              </Text>
            )}
          </Stack>

          <Stack gap="xs" align="flex-end">
            <StatusBadge status={release.status} />
            <Group gap="xs">
              <Text size="sm" c="dimmed">
                {formatFileSize(release.size)}
              </Text>
              {release.quality && (
                <Badge variant="light" color="blue" radius="sm">
                  {release.quality}
                </Badge>
              )}
            </Group>
          </Stack>
        </Group>

        {isActive && (
          <Stack gap={4}>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {t('releaseCard.progress', { defaultValue: 'Progress' })}
              </Text>
              <Text size="sm" c="dimmed">
                {formatProgress(progress)}
              </Text>
            </Group>
            <Progress value={progress} radius="xl" animated={release.status === 'downloading'} />
          </Stack>
        )}

        {!isComplete && (
          <Group gap="xs">
            <Badge variant="light" color="blue" radius="sm">
              {formatFileSize(downloadedBytes)} / {formatFileSize(release.size)}
            </Badge>
            {release.download_speed > 0 && (
              <Badge variant="light" color="blue" radius="sm">
                ↓ {formatSpeed(release.download_speed)}
              </Badge>
            )}
            {eta && (
              <Badge variant="light" color="blue" radius="sm">
                ETA {eta}
              </Badge>
            )}
            {release.upload_speed > 0 && (
              <Badge variant="light" color="cyan" radius="sm">
                ↑ {formatSpeed(release.upload_speed)}
              </Badge>
            )}
          </Group>
        )}

        <Group gap="lg" fz="xs" c="dimmed">
          <Text size="xs">Seeders: {release.seeders}</Text>
          <Text size="xs">Leechers: {release.leechers}</Text>
          <Text size="xs">Ratio: {formatRatio(release.ratio)}</Text>
          <Text size="xs" c={healthColor(health)}>
            Health: {health}%
          </Text>
        </Group>

        {relatedRequests.length > 0 && (
          <Stack gap={6}>
            <Text size="sm" fw={600} c="dimmed">
              {t('releaseCard.relatedRequests', { defaultValue: 'Related requests' })}
            </Text>
            <Group gap="xs">
              {relatedRequests.map((id) => (
                <Badge key={id} variant="light" color="blue" radius="xl">
                  {relatedRequestTitles.get(id) ?? id}
                </Badge>
              ))}
            </Group>
          </Stack>
        )}

        <Group justify="space-between" align="center" wrap="wrap" gap="md">
          <Stack gap={4}>
            <Group gap="md" fz="sm" c="dimmed">
              <Text size="sm">📁 {release.files?.length ?? 0} files</Text>
              {files.video.length > 0 && <Text size="sm">🎬 {files.video.length} video</Text>}
              {files.subtitle.length > 0 && (
                <Text size="sm">📝 {files.subtitle.length} subtitle</Text>
              )}
            </Group>
            <Group gap="md" fz="xs" c="dimmed">
              <Text size="xs">Added: {formatDateTime(release.added_date)}</Text>
              {release.completed_date && (
                <Text size="xs">Completed: {formatDateTime(release.completed_date)}</Text>
              )}
            </Group>
          </Stack>

          <Group gap="xs">
            <Button size="xs" onClick={() => onViewFiles(release)} disabled={isBusy}>
              {t('releaseCard.buttons.files')}
            </Button>

            {isActive && release.status === 'downloading' && (
              <Button
                size="xs"
                color="orange"
                variant="light"
                onClick={() => onPause(release.id)}
                disabled={isBusy}
              >
                {t('releaseCard.buttons.pause')}
              </Button>
            )}

            {release.status === 'pending' && (
              <Button
                size="xs"
                color="teal"
                variant="light"
                onClick={() => onResume(release.id)}
                disabled={isBusy}
              >
                {t('releaseCard.buttons.resume')}
              </Button>
            )}

            <Tooltip label={t('releaseCard.aria.delete')}>
              <ActionIcon
                variant="subtle"
                color="red"
                onClick={confirmDelete}
                disabled={isBusy}
                aria-label={t('releaseCard.aria.delete')}
              >
                <IconTrash size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}
