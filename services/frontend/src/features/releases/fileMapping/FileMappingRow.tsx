import { Badge, Group, NumberInput, Paper, Select, Stack, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import type { MappingDraft } from '@/features/releases/fileMapping/useFileMappingForm';
import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest, ReleaseFile } from '@/types';
import { formatEpisodeCode, isVideoFile } from '@/utils/files';
import { formatFileSize } from '@/utils/formatters';

const optionLabel = (request: MediaRequest) => `${request.title} (${request.year})`;

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
  const isMobile = useIsMobile();
  const existing = file.request_mapping;
  const isSeries = draft.mappingType === 'series';

  const options = requests.map((request) => ({
    value: request.id,
    label: optionLabel(request),
  }));

  const selected = requests.find((request) => request.id === draft.requestId);

  // The request needs the whole row on a phone; the episode fields go below it.
  const selectFlex = isMobile ? '1 1 100%' : '1 1 260px';
  const episodeFieldsFlex = isMobile ? '1 1 100%' : '1 1 200px';

  return (
    <Paper withBorder radius="md" p="md" bg={existing ? 'rgba(59, 130, 246, 0.08)' : undefined}>
      <Stack gap="sm">
        <Stack gap={6}>
          {/*
            Shown in full, never clamped: the episode number that distinguishes
            one file from the next sits at the end of these names, so cutting the
            tail off is what makes a row impossible to map with confidence.
          */}
          <Group gap="xs" wrap="nowrap" align="flex-start">
            <Text>{isVideoFile(file.name) ? '🎬' : '📄'}</Text>
            <Text fw={600} className="break-anywhere" style={{ minWidth: 0 }}>
              {file.name}
            </Text>
          </Group>

          <Group gap="xs" wrap="wrap">
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
        </Stack>

        {existing && (
          <Text size="sm" c="dimmed" className="break-anywhere">
            {t('fileMapping.current', { defaultValue: 'Current' })}:{' '}
            {existing.request_title || existing.request_id}
            {existing.mapping_type === 'series' &&
              ` — ${formatEpisodeCode(existing.season, existing.episode)}`}
          </Text>
        )}

        <Group align="flex-start" wrap="wrap" gap="sm">
          <Stack gap={4} style={{ flex: selectFlex, minWidth: 0 }}>
            <Select
              label={t('fileMapping.request', { defaultValue: 'Request' })}
              placeholder={t('fileMapping.selectRequest', { defaultValue: 'Select a request...' })}
              data={options}
              value={draft.requestId || null}
              disabled={requestsDisabled}
              searchable
              clearable
              onChange={(value) =>
                onSelectRequest(requests.find((request) => request.id === value) ?? null)
              }
            />
            {/*
              A select renders a single-line input, so a long series title is cut
              off no matter how wide the field is. Repeat it underneath where it
              can wrap, so the chosen request is always legible.
            */}
            {selected && (
              <Text size="xs" c="dimmed" className="break-anywhere">
                {optionLabel(selected)}
              </Text>
            )}
          </Stack>

          {isSeries && (
            <Group gap="sm" wrap="nowrap" style={{ flex: episodeFieldsFlex, minWidth: 0 }}>
              <NumberInput
                label={t('fileMapping.season', { defaultValue: 'Season' })}
                min={1}
                inputMode="numeric"
                style={{ flex: 1, minWidth: 0 }}
                value={draft.season ?? ''}
                onChange={(value) =>
                  onChange({ season: typeof value === 'number' ? value : undefined })
                }
              />
              <NumberInput
                label={t('fileMapping.episode', { defaultValue: 'Episode' })}
                min={1}
                inputMode="numeric"
                style={{ flex: 1, minWidth: 0 }}
                value={draft.episode ?? ''}
                onChange={(value) =>
                  onChange({ episode: typeof value === 'number' ? value : undefined })
                }
              />
            </Group>
          )}
        </Group>
      </Stack>
    </Paper>
  );
}
