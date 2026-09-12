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
import { useIsMobile } from '@/hooks/useIsMobile';
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
  const isMobile = useIsMobile();

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

  // Actions take a full-width row of their own on a phone, where a row of `xs`
  // buttons squeezed beside the file counts is both hard to hit and hard to read.
  const actionSize = isMobile ? 'sm' : 'xs';
  const actionFlex = isMobile ? 1 : undefined;
  const actionRowFlex = isMobile ? '1 1 100%' : undefined;

  return (
    <Card withBorder radius="lg" padding={isMobile ? 'md' : 'lg'}>
      <Stack gap="md">
        <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
          {/*
            A `flex-basis` of 0 would let the name collapse to a few characters
            beside the badges rather than pushing them onto their own line.
          */}
          <Stack gap={4} style={{ flex: '1 1 200px', minWidth: 0 }}>
            <Text fw={700} lineClamp={2} className="break-anywhere">
              {release.name}
            </Text>
            {release.torrent_source && (
              <Text size="sm" c="dimmed" className="break-anywhere">
                {t('releaseCard.source')}: {release.torrent_source}
              </Text>
            )}
          </Stack>

          <Group gap="xs" align="center" wrap="nowrap">
            <StatusBadge status={release.status} />
            <Text size="sm" c="dimmed">
              {formatFileSize(release.size)}
            </Text>
            {release.quality && (
              <Badge variant="light" color="blue" radius="sm">
                {release.quality}
              </Badge>
            )}
          </Group>
        </Group>

        {isActive && (
          <Stack gap={4}>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                {t('releaseCard.progress')}
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

        <Group gap="md" fz="xs" c="dimmed" wrap="wrap">
          <Text size="xs">
            {t('releaseCard.stats.seeders')}: {release.seeders}
          </Text>
          <Text size="xs">
            {t('releaseCard.stats.leechers')}: {release.leechers}
          </Text>
          <Text size="xs">
            {t('releaseCard.stats.ratio')}: {formatRatio(release.ratio)}
          </Text>
          <Text size="xs" c={healthColor(health)}>
            {t('releaseCard.stats.health')}: {health}%
          </Text>
        </Group>

        {relatedRequests.length > 0 && (
          <Stack gap={6}>
            <Text size="sm" fw={600} c="dimmed">
              {t('releaseCard.relatedRequests')}
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
          <Stack gap={4} style={{ flex: '1 1 200px', minWidth: 0 }}>
            <Group gap="md" fz="sm" c="dimmed" wrap="wrap">
              <Text size="sm">
                📁 {t('releaseCard.files.total', { count: release.files?.length ?? 0 })}
              </Text>
              {files.video.length > 0 && (
                <Text size="sm">
                  🎬 {t('releaseCard.files.video', { count: files.video.length })}
                </Text>
              )}
              {files.subtitle.length > 0 && (
                <Text size="sm">
                  📝 {t('releaseCard.files.subtitle', { count: files.subtitle.length })}
                </Text>
              )}
            </Group>
            <Group gap="md" fz="xs" c="dimmed" wrap="wrap">
              <Text size="xs">
                {t('releaseCard.added', { date: formatDateTime(release.added_date) })}
              </Text>
              {release.completed_date && (
                <Text size="xs">
                  {t('releaseCard.completed', { date: formatDateTime(release.completed_date) })}
                </Text>
              )}
            </Group>
          </Stack>

          <Group gap="xs" wrap="nowrap" style={{ flex: actionRowFlex }}>
            <Button
              size={actionSize}
              onClick={() => onViewFiles(release)}
              disabled={isBusy}
              style={{ flex: actionFlex }}
            >
              {t('releaseCard.buttons.files')}
            </Button>

            {isActive && release.status === 'downloading' && (
              <Button
                size={actionSize}
                color="orange"
                variant="light"
                onClick={() => onPause(release.id)}
                disabled={isBusy}
                style={{ flex: actionFlex }}
              >
                {t('releaseCard.buttons.pause')}
              </Button>
            )}

            {release.status === 'pending' && (
              <Button
                size={actionSize}
                color="teal"
                variant="light"
                onClick={() => onResume(release.id)}
                disabled={isBusy}
                style={{ flex: actionFlex }}
              >
                {t('releaseCard.buttons.resume')}
              </Button>
            )}

            <Tooltip label={t('releaseCard.aria.delete')}>
              <ActionIcon
                variant="subtle"
                color="red"
                size={isMobile ? 'lg' : 'md'}
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
