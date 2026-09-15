import { Alert, Stack, Text } from '@mantine/core';
import { IconAlertTriangle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import type { RequestWarning } from '@/types';

interface RequestWarningsProps {
  warnings: RequestWarning[] | undefined;
}

const messageKey = (code: RequestWarning['code']): string =>
  code === 'mapping_overlap'
    ? 'requestPage.warnings.mappingOverlap'
    : 'requestPage.warnings.regrabIndexerUnavailable';

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
      {warnings.map((warning, index) => {
        const reason = typeof warning.details?.reason === 'string' ? warning.details.reason : null;
        return (
          <Alert
            key={`${warning.code}-${warning.release_id ?? 'request'}-${index}`}
            variant="light"
            color="yellow"
            icon={<IconAlertTriangle size={16} />}
          >
            {t(messageKey(warning.code), { reason: reason ?? t('requestPage.warnings.unknownReason') })}
          </Alert>
        );
      })}
    </Stack>
  );
}
