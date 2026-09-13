import { Button, Group, Select } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest } from '@/types';

interface FileMappingToolbarProps {
  requests: MediaRequest[];
  requestsLoading: boolean;
  canSuggest: boolean;
  canNumberEpisodes: boolean;
  hasChanges: boolean;
  onApplyToAll: (request: MediaRequest) => void;
  onApplySuggestions: () => void;
  onNumberEpisodes: () => void;
  onReset: () => void;
}

export function FileMappingToolbar({
  requests,
  requestsLoading,
  canSuggest,
  canNumberEpisodes,
  hasChanges,
  onApplyToAll,
  onApplySuggestions,
  onNumberEpisodes,
  onReset,
}: FileMappingToolbarProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  const options = requests.map((request) => ({
    value: request.id,
    label: `${request.title} (${request.year})`,
  }));

  /*
   * These labels are long enough that sharing a row on a phone leaves the text
   * narrower than the button's padding allows, so each takes its own row. On
   * wider screens they keep their natural width: growing them would let
   * flexbox shrink the labels below their content.
   */
  const buttonFlex = isMobile ? '1 1 100%' : undefined;

  return (
    <Group align="flex-end" gap="sm" wrap="wrap" w="100%">
      <Select
        label={t('fileMapping.applyToAll', { defaultValue: 'Apply request to all video files' })}
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
        w={{ base: '100%', sm: 260 }}
      />

      <Group gap="sm" wrap="wrap" w={{ base: '100%', sm: 'auto' }}>
        <Button
          variant="default"
          onClick={onApplySuggestions}
          disabled={!canSuggest}
          style={{ flex: buttonFlex }}
        >
          {t('fileMapping.applySuggestions', { defaultValue: 'Use suggested mapping' })}
        </Button>

        <Button
          variant="default"
          onClick={onNumberEpisodes}
          disabled={!canNumberEpisodes}
          style={{ flex: buttonFlex }}
        >
          {t('fileMapping.numberEpisodes', { defaultValue: 'Number episodes in order' })}
        </Button>

        <Button
          variant="default"
          onClick={onReset}
          disabled={!hasChanges}
          style={{ flex: buttonFlex }}
        >
          {t('fileMapping.reset', { defaultValue: 'Reset changes' })}
        </Button>
      </Group>
    </Group>
  );
}
