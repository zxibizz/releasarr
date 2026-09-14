import { Group, Paper, Stack, Tabs, Text, Tooltip } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { OtherFilesSection } from '@/features/releases/components/OtherFilesSection';
import { FileMappingForm } from '@/features/releases/fileMapping/FileMappingForm';
import type { MediaRequest, Release, ReleaseFile } from '@/types';
import { overlapRelatedReleaseCount, overlappingFileIds } from '@/features/releases/warnings';
import { formatEpisodeCode, splitVideoFiles } from '@/utils/files';
import { formatFileSize } from '@/utils/formatters';

function ReleaseFileCard({
  file,
  overlapping,
  relatedReleaseCount,
}: {
  file: ReleaseFile;
  overlapping: boolean;
  relatedReleaseCount: number;
}) {
  const { t } = useTranslation();
  const mapping = file.request_mapping;

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap={6}>
        <Group gap={6} wrap="nowrap" align="center">
          <Text fw={600} className="break-anywhere" style={{ flex: 1 }}>
            {file.name}
          </Text>
          {overlapping && (
            <Tooltip
              label={
                relatedReleaseCount > 0
                  ? t('releaseCard.overlapWarning.withOtherReleases', {
                      count: relatedReleaseCount,
                    })
                  : t('releaseCard.overlapWarning.withinRelease')
              }
            >
              <IconAlertTriangle size={16} color="var(--mantine-color-yellow-6)" />
            </Tooltip>
          )}
        </Group>
        <Text size="sm" c="dimmed">
          {formatFileSize(file.size)}
        </Text>
        <Text size="sm" c="dimmed">
          {t('filesModal.mapping', { defaultValue: 'Mapping' })}:{' '}
          {mapping
            ? `${mapping.request_title || mapping.request_id}${
                mapping.mapping_type === 'series'
                  ? ` — ${formatEpisodeCode(mapping.season, mapping.episode)}`
                  : ''
              }`
            : t('filesModal.notMapped', { defaultValue: 'Not mapped' })}
        </Text>
      </Stack>
    </Paper>
  );
}

interface ReleaseFilesModalProps {
  release: Release | null;
  currentRequest: MediaRequest;
  opened: boolean;
  onClose: () => void;
}

export function ReleaseFilesModal({
  release,
  currentRequest,
  opened,
  onClose,
}: ReleaseFilesModalProps) {
  const { t } = useTranslation();

  if (!release) {
    return null;
  }

  const { video, other } = splitVideoFiles(release.files);
  const overlappingIds = overlappingFileIds(release);
  const relatedReleaseCount = overlapRelatedReleaseCount(release);

  return (
    <ResponsiveModal opened={opened} onClose={onClose} title={`📁 ${release.name}`}>
      <Tabs defaultValue="files">
        <Tabs.List grow>
          <Tabs.Tab value="files">{t('filesModal.tabs.files', { defaultValue: 'Files' })}</Tabs.Tab>
          <Tabs.Tab value="mapping">
            {t('filesModal.tabs.mapping', { defaultValue: 'Mapping' })}
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="files" pt="md">
          <Stack gap="sm">
            {video.map((file) => (
              <ReleaseFileCard
                key={file.id}
                file={file}
                overlapping={overlappingIds.has(file.id)}
                relatedReleaseCount={relatedReleaseCount}
              />
            ))}
            <OtherFilesSection count={other.length}>
              {other.map((file) => (
                <ReleaseFileCard
                  key={file.id}
                  file={file}
                  overlapping={overlappingIds.has(file.id)}
                  relatedReleaseCount={relatedReleaseCount}
                />
              ))}
            </OtherFilesSection>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="mapping" pt="md">
          <FileMappingForm
            releaseId={release.id}
            requestId={currentRequest.id}
            files={release.files}
          />
        </Tabs.Panel>
      </Tabs>
    </ResponsiveModal>
  );
}
