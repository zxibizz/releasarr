import { Alert, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import type { RequestWarning } from '@/types';

interface RequestWarningsProps {
  warnings: RequestWarning[] | undefined;
}

/**
 * One string per code. A record rather than a ternary so a code added to the
 * contract fails to compile here instead of silently rendering another code's
 * message.
 */
const MESSAGE_KEYS: Record<RequestWarning['code'], string> = {
  mapping_overlap: 'requestPage.warnings.mappingOverlap',
  regrab_indexer_unavailable: 'requestPage.warnings.regrabIndexerUnavailable',
  release_not_listed: 'requestPage.warnings.releaseNotListed',
};

const detailString = (warning: RequestWarning, key: string): string | null => {
  const value = warning.details?.[key];
  return typeof value === 'string' ? value : null;
};

export function RequestWarnings({ warnings }: RequestWarningsProps) {
  const { t } = useTranslation();

  if (!warnings || warnings.length === 0) {
    return null;
  }

  return (
    <Stack gap="sm">
      <Text size="sm" fw={600} tt="uppercase" c="dimmed">
        {t('requestPage.warnings.title')}
      </Text>
      {warnings.map((warning, index) => (
        <Alert
          key={`${warning.code}-${warning.release_id ?? 'request'}-${index}`}
          variant="light"
          color="yellow"
          icon={<IconAlertTriangle size={16} />}
        >
          {t(MESSAGE_KEYS[warning.code], {
            // Each message interpolates one of these; i18next ignores the other.
            indexer: detailString(warning, 'indexer') ?? t('requestPage.warnings.unknownIndexer'),
            reason: detailString(warning, 'reason') ?? t('requestPage.warnings.unknownReason'),
          })}
        </Alert>
      ))}
    </Stack>
  );
}
