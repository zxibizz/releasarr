import { Center, Loader, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { IntegrationCard } from '@/features/settings/components/IntegrationCard';
import { IntegrationSettingsModal } from '@/features/settings/components/IntegrationSettingsModal';
import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';
import { useSettings, useTestConnection } from '@/features/settings/queries';
import {
  fieldsForIntegration,
  isIntegrationConfigured,
  METADATA_PROVIDERS,
  type MetadataProvider,
  urlKeyFor,
} from '@/features/settings/serviceFields';
import { flattenSettingValues } from '@/features/settings/values';

export function MetadataSettingsPage() {
  const { t } = useTranslation();
  const settings = useSettings();
  const test = useTestConnection();
  const [editing, setEditing] = useState<MetadataProvider | null>(null);

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
        <Title order={2}>{t('settings.metadata.title')}</Title>
        <Text c="dimmed" size="sm" mt={4}>
          {t('settings.metadata.description')}
        </Text>
      </div>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {METADATA_PROVIDERS.map((provider) => (
          <IntegrationCard
            key={provider}
            integration={provider}
            url={String(values[urlKeyFor(provider)] ?? '')}
            configured={isIntegrationConfigured(provider, (key) => values[key])}
            testing={test.isPending && test.variables?.integration === provider}
            onTest={() => test.mutate({ integration: provider })}
            onEdit={() => setEditing(provider)}
          />
        ))}
      </SimpleGrid>

      {/* Languages belong to neither provider, so no panel claims them. */}
      <SettingsSectionForm
        section="metadata"
        titleKey="settings.metadata.shared"
        titleOrder={3}
        includeField={(field) => !field.key.startsWith('tvdb_') && !field.key.startsWith('tmdb_')}
      />

      {editing && (
        <IntegrationSettingsModal
          key={editing}
          integration={editing}
          primarySection="metadata"
          fields={fieldsForIntegration(fields, editing)}
          values={values}
          onClose={() => setEditing(null)}
        />
      )}
    </Stack>
  );
}
