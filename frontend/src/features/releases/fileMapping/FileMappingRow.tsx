import { Badge, Group, NumberInput, Paper, Select, Stack, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import type { MappingDraft } from '@/features/releases/fileMapping/useFileMappingForm';
import type { MediaRequest, ReleaseFile } from '@/types';
import { formatEpisodeCode, isVideoFile } from '@/utils/files';
import { formatFileSize } from '@/utils/formatters';

interface FileMappingRowProps {
  file: ReleaseFile;
  draft: MappingDraft;
  requests: MediaRequest[];
  requestsDisabled: boolean;
  isDirty: boolean;
  onSelectRequest: (request: MediaRequest | null) => void;
  onChange: (changes: Partial<MappingDraft>) => void;
}

export function FileMappingRow({
  file,
  draft,
  requests,
  requestsDisabled,
  isDirty,
  onSelectRequest,
  onChange,
}: FileMappingRowProps) {
  const { t } = useTranslation();
  const existing = file.request_mapping;
  const isSeries = draft.mappingType === 'series';

  const options = requests.map((request) => ({
    value: request.id,
    label: `${request.title} (${request.year})`,
  }));

  return (
    <Paper withBorder radius="md" p="md" bg={existing ? 'rgba(59, 130, 246, 0.08)' : undefined}>
      <Stack gap="sm">
        <Group gap="xs" wrap="nowrap">
          <Text>{isVideoFile(file.name) ? '🎬' : '📄'}</Text>
          <Text fw={600} lineClamp={1} style={{ flex: 1, minWidth: 0 }}>
            {file.name}
          </Text>
          <Text size="xs" c="dimmed">
            {formatFileSize(file.size)}
          </Text>
          {existing && (
            <Badge size="sm" variant="light" color="blue">
              {t('fileMapping.mapped', { defaultValue: 'Mapped' })}
            </Badge>
          )}
          {isDirty && (
            <Badge size="sm" variant="light" color="yellow">
              {t('fileMapping.changed', { defaultValue: 'Changed' })}
            </Badge>
          )}
        </Group>

        {existing && (
          <Text size="sm" c="dimmed">
            {t('fileMapping.current', { defaultValue: 'Current' })}:{' '}
            {existing.request_title || existing.request_id}
            {existing.mapping_type === 'series' &&
              ` — ${formatEpisodeCode(existing.season, existing.episode)}`}
          </Text>
        )}

        <Group align="flex-start" wrap="wrap" gap="sm">
          <Select
            label={t('fileMapping.request', { defaultValue: 'Request' })}
            placeholder={t('fileMapping.selectRequest', { defaultValue: 'Select a request...' })}
            data={options}
            value={draft.requestId || null}
            disabled={requestsDisabled}
            searchable
            clearable
            style={{ flex: 1, minWidth: 220 }}
            onChange={(value) =>
              onSelectRequest(requests.find((request) => request.id === value) ?? null)
            }
          />

          {isSeries && (
            <NumberInput
              label={t('fileMapping.season', { defaultValue: 'Season' })}
              min={1}
              w={110}
              value={draft.season ?? ''}
              onChange={(value) =>
                onChange({ season: typeof value === 'number' ? value : undefined })
              }
            />
          )}

          {isSeries && (
            <NumberInput
              label={t('fileMapping.episode', { defaultValue: 'Episode' })}
              min={1}
              w={110}
              value={draft.episode ?? ''}
              onChange={(value) =>
                onChange({ episode: typeof value === 'number' ? value : undefined })
              }
            />
          )}
        </Group>
      </Stack>
    </Paper>
  );
}
