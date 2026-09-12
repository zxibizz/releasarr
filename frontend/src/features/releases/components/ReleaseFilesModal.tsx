import { Modal, Paper, Stack, Tabs, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { FileMappingForm } from '@/features/releases/fileMapping/FileMappingForm';
import type { DefaultRequest } from '@/features/releases/fileMapping/useFileMappingForm';
import type { MediaRequest, Release } from '@/types';
import { formatEpisodeCode } from '@/utils/files';
import { formatFileSize } from '@/utils/formatters';

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

  const isSeries = currentRequest.type === 'series';
  const defaultRequest: DefaultRequest = {
    id: currentRequest.id,
    title: currentRequest.title,
    type: isSeries ? 'series' : 'movie',
    seasonNumber: isSeries ? currentRequest.season_number : undefined,
    seriesTitle: isSeries ? currentRequest.series_title : undefined,
    sonarrSeriesId: isSeries ? currentRequest.sonarr_series_id : undefined,
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      title={`📁 ${release.name}`}
    >
      <Tabs defaultValue="files">
        <Tabs.List>
          <Tabs.Tab value="files">{t('filesModal.tabs.files', { defaultValue: 'Files' })}</Tabs.Tab>
          <Tabs.Tab value="mapping">
            {t('filesModal.tabs.mapping', { defaultValue: 'Mapping' })}
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="files" pt="md">
          <Stack gap="sm">
            {release.files.map((file) => (
              <Paper key={file.id} withBorder radius="md" p="md">
                <Stack gap={6}>
                  <Text fw={600} style={{ wordBreak: 'break-all' }}>
                    {file.name}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {formatFileSize(file.size)}
                  </Text>
                  <Text size="sm" c="dimmed">
                    {t('filesModal.mapping', { defaultValue: 'Mapping' })}:{' '}
                    {file.request_mapping
                      ? `${file.request_mapping.request_title || file.request_mapping.request_id}${
                          file.request_mapping.mapping_type === 'series'
                            ? ` — ${formatEpisodeCode(
                                file.request_mapping.season,
                                file.request_mapping.episode,
                              )}`
                            : ''
                        }`
                      : t('filesModal.notMapped', { defaultValue: 'Not mapped' })}
                  </Text>
                </Stack>
              </Paper>
            ))}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="mapping" pt="md">
          <FileMappingForm
            releaseId={release.id}
            requestId={currentRequest.id}
            files={release.files}
            defaultRequest={defaultRequest}
          />
        </Tabs.Panel>
      </Tabs>
    </Modal>
  );
}
