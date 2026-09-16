import { Alert, Anchor, Badge, Group, Paper, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';

import { DataField } from '@/components/DataField';
import { StatusBadge } from '@/components/StatusBadge';
import { healthColor, releaseAgeLabel, releaseHealthScore } from '@/features/releases/formatting';
import { relatedRequestIds, useRelatedRequestTitles } from '@/features/releases/relatedRequests';
import {
  hasMappingOverlap,
  missingRegrabFileCount,
  notListedIndexer,
  overlapRelatedReleaseCount,
  regrabUnavailableReason,
  unmappedRegrabFileCount,
} from '@/features/releases/warnings';
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

/**
 * One sentence per warning, in the words the badges and tooltips already use.
 * Written out here rather than reused from `RequestWarnings`, which reads a
 * warning's id and timestamp and so cannot take a release's narrower shape.
 */
const warningMessages = (release: Release, t: TFunction): string[] => {
  const messages: string[] = [];

  if (hasMappingOverlap(release)) {
    const related = overlapRelatedReleaseCount(release);
    messages.push(
      related > 0
        ? t('releaseCard.overlapWarning.withOtherReleases', { count: related })
        : t('releaseCard.overlapWarning.withinRelease'),
    );
  }

  const regrabReason = regrabUnavailableReason(release);
  if (regrabReason) {
    messages.push(t('requestPage.warnings.regrabIndexerUnavailable', { reason: regrabReason }));
  }

  const indexer = notListedIndexer(release);
  if (indexer) {
    messages.push(t('releaseCard.notListedWarning.tooltip', { indexer }));
  }

  const unmapped = unmappedRegrabFileCount(release);
  if (unmapped !== null) {
    messages.push(t('requestPage.warnings.regrabFilesUnmapped', { count: unmapped }));
  }

  const missing = missingRegrabFileCount(release);
  if (missing !== null) {
    messages.push(t('requestPage.warnings.regrabFilesMissing', { count: missing }));
  }

  return messages;
};

interface ReleaseGeneralTabProps {
  release: Release;
  currentRequestId: string;
}

/** Everything the release row itself knows, laid out as label/value pairs. */
export function ReleaseGeneralTab({ release, currentRequestId }: ReleaseGeneralTabProps) {
  const { t } = useTranslation();
  const relatedRequestTitles = useRelatedRequestTitles();

  const files = groupFilesByType(release.files ?? []);
  const health = releaseHealthScore(release);
  const isComplete = release.status === 'completed';
  const progress = isComplete ? 100 : release.progress;
  const downloadedBytes = Math.round((progress / 100) * release.size);
  const eta =
    release.status === 'downloading'
      ? calculateEta(release.size, downloadedBytes, release.download_speed)
      : null;

  const relatedRequests = relatedRequestIds(release, currentRequestId);
  const warnings = warningMessages(release, t);

  return (
    <Stack gap="md">
      <Paper withBorder radius="md" p="md">
        <Stack gap="sm">
          <DataField label={t('releaseDetails.general.status')}>
            <StatusBadge status={release.status} />
          </DataField>

          {release.quality && (
            <DataField label={t('releaseDetails.general.quality')}>
              <Badge variant="light" color="blue" radius="sm">
                {release.quality}
              </Badge>
            </DataField>
          )}

          <DataField label={t('releaseDetails.general.size')}>
            <Text size="sm">{formatFileSize(release.size)}</Text>
          </DataField>

          {(release.torrent_source || release.info_url) && (
            <DataField label={t('releaseDetails.general.source')}>
              {release.info_url ? (
                <Anchor
                  href={release.info_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="sm"
                  className="break-anywhere"
                >
                  {release.torrent_source ?? t('releaseCard.links.tracker')} ↗
                </Anchor>
              ) : (
                <Text size="sm" className="break-anywhere">
                  {release.torrent_source}
                </Text>
              )}
            </DataField>
          )}

          <DataField label={t('releaseDetails.general.hash')}>
            <Text size="sm" ff="monospace" className="break-anywhere">
              {release.hash}
            </Text>
          </DataField>

          {release.published_date && (
            <DataField label={t('releaseDetails.general.published')}>
              <Text size="sm">
                {formatDateTime(release.published_date)} · {releaseAgeLabel(release, t)}
              </Text>
            </DataField>
          )}

          <DataField label={t('releaseDetails.general.added')}>
            <Text size="sm">{formatDateTime(release.added_date)}</Text>
          </DataField>

          {release.completed_date && (
            <DataField label={t('releaseDetails.general.completed')}>
              <Text size="sm">{formatDateTime(release.completed_date)}</Text>
            </DataField>
          )}
        </Stack>
      </Paper>

      <Paper withBorder radius="md" p="md">
        <Stack gap="sm">
          <DataField label={t('releaseCard.progress')}>
            <Text size="sm">{formatProgress(progress)}</Text>
          </DataField>

          {/* A finished release has no remaining bytes or rate worth a row. */}
          {!isComplete && (
            <DataField label={t('releaseDetails.general.downloaded')}>
              <Text size="sm">
                {formatFileSize(downloadedBytes)} / {formatFileSize(release.size)}
              </Text>
            </DataField>
          )}

          {!isComplete && release.download_speed > 0 && (
            <DataField label={t('releaseDetails.general.downloadSpeed')}>
              <Text size="sm">{formatSpeed(release.download_speed)}</Text>
            </DataField>
          )}

          {release.upload_speed > 0 && (
            <DataField label={t('releaseDetails.general.uploadSpeed')}>
              <Text size="sm">{formatSpeed(release.upload_speed)}</Text>
            </DataField>
          )}

          {eta && (
            <DataField label={t('releaseDetails.general.eta')}>
              <Text size="sm">{eta}</Text>
            </DataField>
          )}

          <DataField label={t('releaseCard.stats.ratio')}>
            <Text size="sm">{formatRatio(release.ratio)}</Text>
          </DataField>

          <DataField label={t('releaseCard.stats.seeders')}>
            <Text size="sm">{release.seeders}</Text>
          </DataField>

          <DataField label={t('releaseCard.stats.leechers')}>
            <Text size="sm">{release.leechers}</Text>
          </DataField>

          <DataField label={t('releaseCard.stats.health')}>
            <Text size="sm" c={healthColor(health)}>
              {health}%
            </Text>
          </DataField>
        </Stack>
      </Paper>

      <Paper withBorder radius="md" p="md">
        <Stack gap="sm">
          <DataField label={t('releaseDetails.general.files')}>
            <Text size="sm">
              {[
                t('releaseCard.files.total', { count: release.files?.length ?? 0 }),
                files.video.length > 0
                  ? t('releaseCard.files.video', { count: files.video.length })
                  : null,
                files.subtitle.length > 0
                  ? t('releaseCard.files.subtitle', { count: files.subtitle.length })
                  : null,
                files.other.length > 0
                  ? t('releaseDetails.general.otherFiles', { count: files.other.length })
                  : null,
              ]
                .filter(Boolean)
                .join(' · ')}
            </Text>
          </DataField>

          {relatedRequests.length > 0 && (
            <DataField label={t('releaseCard.relatedRequests')}>
              <Group gap="xs" justify="flex-end">
                {relatedRequests.map((id) => (
                  <Badge key={id} variant="light" color="blue" radius="xl">
                    {relatedRequestTitles.get(id) ?? id}
                  </Badge>
                ))}
              </Group>
            </DataField>
          )}
        </Stack>
      </Paper>

      {warnings.length > 0 && (
        <Stack gap="sm">
          <Text size="sm" fw={600} tt="uppercase" c="dimmed">
            {t('requestPage.warnings.title')}
          </Text>
          {warnings.map((message) => (
            <Alert
              key={message}
              variant="light"
              color="yellow"
              icon={<IconAlertTriangle size={16} />}
            >
              {message}
            </Alert>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
