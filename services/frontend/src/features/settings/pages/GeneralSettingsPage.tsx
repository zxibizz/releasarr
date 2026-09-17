import { Card, Group, Stack, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';

export function GeneralSettingsPage() {
  const { t } = useTranslation();

  return (
    <Stack gap="lg">
      <SettingsSectionForm
        section="general"
        titleKey="settings.general.title"
        descriptionKey="settings.general.description"
      />
      <Card withBorder padding="md">
        <Group justify="space-between" wrap="nowrap">
          <Text fw={500}>{t('settings.general.language')}</Text>
          <LanguageSwitcher size="sm" w={180} />
        </Group>
      </Card>
    </Stack>
  );
}
