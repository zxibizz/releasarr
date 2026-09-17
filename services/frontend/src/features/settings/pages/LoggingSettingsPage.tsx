import { Anchor, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';

export function LoggingSettingsPage() {
  const { t } = useTranslation();

  return (
    <div>
      <SettingsSectionForm
        section="logging"
        titleKey="settings.logging.title"
        descriptionKey="settings.logging.description"
      />
      <Text c="dimmed" size="sm" mt="md">
        <Anchor component={Link} to="/system/logs" size="sm">
          {t('settings.logging.viewSystem')}
        </Anchor>
      </Text>
    </div>
  );
}
