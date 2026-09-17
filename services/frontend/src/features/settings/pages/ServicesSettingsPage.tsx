import { Center, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ServiceCard } from '@/features/settings/components/ServiceCard';
import { ServiceSettingsModal } from '@/features/settings/components/ServiceSettingsModal';
import { useSettings, useTestConnection } from '@/features/settings/queries';
import {
  fieldsForService,
  isServiceConfigured,
  SERVICE_INTEGRATIONS,
  type ServiceIntegration,
} from '@/features/settings/serviceFields';
import type { SettingsResponse } from '@/types';

/** Field keys are unique across sections, so the sections flatten into one lookup. */
function flattenValues(settings: SettingsResponse): Record<string, unknown> {
  return Object.assign({}, ...Object.values(settings.values)) as Record<string, unknown>;
}

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

  const values = flattenValues(settings.data);
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
          <ServiceCard
            key={integration}
            integration={integration}
            url={String(values[`${integration}_url`] ?? '')}
            configured={isServiceConfigured(integration, (key) => values[key])}
            testing={test.isPending && test.variables?.integration === integration}
            onTest={() => test.mutate({ integration })}
            onEdit={() => setEditing(integration)}
          />
        ))}
      </SimpleGrid>

      {/* Keyed and mounted only while open so each edit starts from an empty draft. */}
      {editing && (
        <ServiceSettingsModal
          key={editing}
          integration={editing}
          fields={fieldsForService(fields, editing)}
          values={values}
          onClose={() => setEditing(null)}
        />
      )}
    </Stack>
  );
}
