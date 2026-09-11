import { Button, Checkbox, Group, Select } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import type { MediaRequest } from '@/types';

interface FileMappingToolbarProps {
  requests: MediaRequest[];
  requestsLoading: boolean;
  videoOnly: boolean;
  videoCount: number;
  canAutoFill: boolean;
  hasChanges: boolean;
  onVideoOnlyChange: (value: boolean) => void;
  onApplyToAll: (request: MediaRequest) => void;
  onAutoFill: () => void;
  onReset: () => void;
}

export function FileMappingToolbar({
  requests,
  requestsLoading,
  videoOnly,
  videoCount,
  canAutoFill,
  hasChanges,
  onVideoOnlyChange,
  onApplyToAll,
  onAutoFill,
  onReset,
}: FileMappingToolbarProps) {
  const { t } = useTranslation();

  const options = requests.map((request) => ({
    value: request.id,
    label: `${request.title} (${request.year})`,
  }));

  return (
    <Group align="flex-end" gap="sm" wrap="wrap">
      <Checkbox
        label={t('fileMapping.videoOnly', {
          defaultValue: 'Show only video files ({{count}})',
          count: videoCount,
        })}
        checked={videoOnly}
        onChange={(event) => onVideoOnlyChange(event.currentTarget.checked)}
      />

      <Select
        label={t('fileMapping.applyToAll', { defaultValue: 'Apply request to all files' })}
        placeholder={
          requestsLoading
            ? t('fileMapping.loadingRequests', { defaultValue: 'Loading requests...' })
            : t('fileMapping.selectRequest', { defaultValue: 'Select a request...' })
        }
        data={options}
        disabled={requestsLoading || options.length === 0}
        searchable
        value={null}
        onChange={(value) => {
          const request = requests.find((item) => item.id === value);
          if (request) {
            onApplyToAll(request);
          }
        }}
        w={260}
      />

      <Button variant="default" onClick={onAutoFill} disabled={!canAutoFill}>
        {t('fileMapping.autoFill', { defaultValue: 'Auto-fill from filenames' })}
      </Button>

      <Button variant="default" onClick={onReset} disabled={!hasChanges}>
        {t('fileMapping.reset', { defaultValue: 'Reset changes' })}
      </Button>
    </Group>
  );
}
