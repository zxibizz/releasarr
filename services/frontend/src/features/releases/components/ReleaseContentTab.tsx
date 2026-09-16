import { Button, Group, Paper, Stack, Text, Tooltip } from '@mantine/core';
import { IconAlertTriangle, IconPencil } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { OtherFilesSection } from '@/features/releases/components/OtherFilesSection';
import { overlapRelatedReleaseCount, overlappingFileIds } from '@/features/releases/warnings';
import type { Release, ReleaseFile } from '@/types';
import { formatFileSize } from '@/utils/formatters';
import { formatEpisodeCode, splitVideoFiles } from '@/utils/files';

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
          {t('releaseDetails.content.mapping')}:{' '}
          {mapping
            ? `${mapping.request_title || mapping.request_id}${
                mapping.mapping_type === 'series'
                  ? ` — ${formatEpisodeCode(mapping.season, mapping.episode)}`
                  : ''
              }`
            : t('releaseDetails.content.notMapped')}
        </Text>
      </Stack>
    </Paper>
  );
}

interface ReleaseContentTabProps {
  release: Release;
  /** Hands the tab over to the mapping editor, which owns the editable rows. */
  onEditMapping: () => void;
}

/**
 * What the release holds and where each file is mapped. Read-only: the mapping
 * editor is a mode the reader asks for, so a glance at the list cannot change
 * anything by accident.
 */
export function ReleaseContentTab({ release, onEditMapping }: ReleaseContentTabProps) {
  const { t } = useTranslation();

  const files = release.files ?? [];
  const { video, other } = splitVideoFiles(files);
  const overlappingIds = overlappingFileIds(release);
  const relatedReleaseCount = overlapRelatedReleaseCount(release);

  const card = (file: ReleaseFile) => (
    <ReleaseFileCard
      key={file.id}
      file={file}
      overlapping={overlappingIds.has(file.id)}
      relatedReleaseCount={relatedReleaseCount}
    />
  );

  if (files.length === 0) {
    return (
      <EmptyState
        icon="📁"
        title={t('releaseDetails.content.empty.title')}
        description={t('releaseDetails.content.empty.description')}
      />
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center" wrap="wrap" gap="sm">
        <Text size="sm" c="dimmed">
          {t('releaseCard.files.total', { count: files.length })}
        </Text>
        {/*
          A label as long as the Russian one needs the whole row: beside the
          count on a phone it is squeezed past its own text and clipped.
        */}
        <Button
          variant="light"
          size="sm"
          leftSection={<IconPencil size={16} />}
          onClick={onEditMapping}
          w={{ base: '100%', sm: 'auto' }}
        >
          {t('releaseDetails.content.editMapping')}
        </Button>
      </Group>

      <Stack gap="sm">
        {video.map(card)}
        <OtherFilesSection count={other.length}>{other.map(card)}</OtherFilesSection>
      </Stack>
    </Stack>
  );
}
