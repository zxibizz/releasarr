import { Paper, Stack, Tabs, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { OtherFilesSection } from '@/features/releases/components/OtherFilesSection';
import { FileMappingForm } from '@/features/releases/fileMapping/FileMappingForm';
import type { MediaRequest, Release, ReleaseFile } from '@/types';
import { formatEpisodeCode, splitVideoFiles } from '@/utils/files';
import { formatFileSize } from '@/utils/formatters';

function ReleaseFileCard({ file }: { file: ReleaseFile }) {
  const { t } = useTranslation();
  const mapping = file.request_mapping;

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap={6}>
        <Text fw={600} className="break-anywhere">
          {file.name}
        </Text>
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
              <ReleaseFileCard key={file.id} file={file} />
            ))}
            <OtherFilesSection count={other.length}>
              {other.map((file) => (
                <ReleaseFileCard key={file.id} file={file} />
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
