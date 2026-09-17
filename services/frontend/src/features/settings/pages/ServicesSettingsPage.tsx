import { Center, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { IntegrationCard } from '@/features/settings/components/IntegrationCard';
import { IntegrationSettingsModal } from '@/features/settings/components/IntegrationSettingsModal';
import { useSettings, useTestConnection } from '@/features/settings/queries';
import {
  fieldsForIntegration,
  isIntegrationConfigured,
  SERVICE_INTEGRATIONS,
  type ServiceIntegration,
  urlKeyFor,
} from '@/features/settings/serviceFields';
import { flattenSettingValues } from '@/features/settings/values';

export function ServicesSettingsPage() {
  const { t } = useTranslation();
  const settings = useSettings();
  const test = useTestConnection();
  const [editing, setEditing] = useState<ServiceIntegration | null>(null);

  if (settings.isPending) {
    return (
      <Center mih="40vh">
        <Loader />
      </Center>
    );
  }

  if (settings.isError) {
    return <Text c="red">{t('settings.loadFailed')}</Text>;
  }

  const values = flattenSettingValues(settings.data);
  const fields = settings.data.fields ?? [];

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>{t('settings.services.title')}</Title>
        <Text c="dimmed" size="sm" mt={4}>
          {t('settings.services.description')}
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {SERVICE_INTEGRATIONS.map((integration) => (
          <IntegrationCard
            key={integration}
            integration={integration}
            url={String(values[urlKeyFor(integration)] ?? '')}
            configured={isIntegrationConfigured(integration, (key) => values[key])}
            testing={test.isPending && test.variables?.integration === integration}
            onTest={() => test.mutate({ integration })}
            onEdit={() => setEditing(integration)}
          />
        ))}
      </SimpleGrid>

      {/* Keyed and mounted only while open so each edit starts from an empty draft. */}
      {editing && (
        <IntegrationSettingsModal
          key={editing}
          integration={editing}
          primarySection="services"
          fields={fieldsForIntegration(fields, editing)}
          values={values}
          onClose={() => setEditing(null)}
        />
      )}
    </Stack>
  );
}
