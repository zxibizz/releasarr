import { Button, Group, Select } from '@mantine/core';
import { IconWand } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useIsMobile } from '@/hooks/useIsMobile';
import type { MediaRequest } from '@/types';

interface FileMappingToolbarProps {
  requests: MediaRequest[];
  requestsLoading: boolean;
  currentRequestId?: string;
  /** False until the automapper's proposals have arrived; see `FileMappingForm`. */
  canAutomap: boolean;
  onApplyToAll: (request: MediaRequest) => void;
  onAutomap: () => void;
}

export function FileMappingToolbar({
  requests,
  requestsLoading,
  currentRequestId,
  canAutomap,
  onApplyToAll,
  onAutomap,
}: FileMappingToolbarProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  // Only a display default: picking a request still requires an explicit choice below.
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  const options = requests.map((request) => ({
    value: request.id,
    label: `${request.title} (${request.year})`,
  }));

  /*
   * The button takes a row of its own on a phone rather than sharing one with
   * the select. On wider screens it keeps its natural width.
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
        value={selectedRequestId ?? currentRequestId ?? null}
        onChange={(value) => {
          setSelectedRequestId(value);
          const request = requests.find((item) => item.id === value);
          if (request) {
            onApplyToAll(request);
          }
        }}
        w={{ base: '100%', sm: 260 }}
      />

      <Button
        variant="default"
        leftSection={<IconWand size={16} />}
        onClick={() => {
          // The rows no longer carry the last pick, so the field above it must
          // stop claiming they do.
          setSelectedRequestId(null);
          onAutomap();
        }}
        disabled={!canAutomap}
        style={{ flex: buttonFlex }}
        /*
         * Mantine clips a Button's label instead of wrapping it - the root's
         * height is fixed and the label is kept on one line - so a translation
         * longer than the button is cut off mid-word. Freed here, so the button
         * grows downwards instead.
         */
        styles={{
          root: { height: 'auto', minHeight: 'var(--button-height-sm)' },
          label: { whiteSpace: 'normal', textAlign: 'center' },
        }}
      >
        {t('fileMapping.automap', { defaultValue: 'Map automatically' })}
      </Button>
    </Group>
  );
}
