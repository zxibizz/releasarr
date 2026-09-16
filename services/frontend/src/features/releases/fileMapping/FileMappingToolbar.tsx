import { Button, Group } from '@mantine/core';
import { IconWand } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { useIsMobile } from '@/hooks/useIsMobile';

interface FileMappingToolbarProps {
  /** False until the automapper's proposals have arrived; see `FileMappingForm`. */
  canAutomap: boolean;
  onAutomap: () => void;
}

export function FileMappingToolbar({ canAutomap, onAutomap }: FileMappingToolbarProps) {
  const { t } = useTranslation();
  const isMobile = useIsMobile();

  /*
   * The button takes a row of its own on a phone. On wider screens it keeps its
   * natural width.
   */
  const buttonFlex = isMobile ? '1 1 100%' : undefined;

  return (
    <Group align="flex-end" gap="sm" wrap="wrap" w="100%">
      <Button
        variant="default"
        leftSection={<IconWand size={16} />}
        onClick={onAutomap}
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
