import { Text, type TextProps } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useSystemInfo } from '@/features/system/queries';

export function AppVersion(props: TextProps) {
  const { t } = useTranslation();
  const { data } = useSystemInfo();

  if (!data) {
    return null;
  }

  return (
    <Text size="xs" c="dimmed" {...props}>
      {t('system.version', { version: data.version })}
    </Text>
  );
}
