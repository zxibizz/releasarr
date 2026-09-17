import { Button, Divider, Group, Stack, Text } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { ResponsiveModal } from '@/components/ResponsiveModal';
import { SettingsField } from '@/features/settings/components/SettingsField';
import { useTestConnection, useUpdateSettingsSections } from '@/features/settings/queries';
import {
  connectionTestPayload,
  labelKeyFor,
  type PanelIntegration,
} from '@/features/settings/serviceFields';
import { useFieldOptions } from '@/features/settings/useFieldOptions';
import type { SettingFieldInfo, SettingsSection } from '@/types';

interface IntegrationSettingsModalProps {
  integration: PanelIntegration;
  /** Every field this integration owns, across sections. */
  fields: SettingFieldInfo[];
  /** Saved values, keyed by field. */
  values: Record<string, unknown>;
  /** The section holding the credentials; the rest are shown as advanced. */
  primarySection: SettingsSection;
  onClose: () => void;
}

/**
 * Edits one integration in isolation. Its fields can be spread across two
 * sections server-side, so the save fans out; the draft is the only source for a
 * connection test, since a saved secret comes back masked.
 */
export function IntegrationSettingsModal({
  integration,
  fields,
  values,
  primarySection,
  onClose,
}: IntegrationSettingsModalProps) {
  const { t } = useTranslation();
  const update = useUpdateSettingsSections();
  const test = useTestConnection();
  const optionsFor = useFieldOptions(integration);
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const valueFor = (key: string) => (key in draft ? draft[key] : values[key]);
  const dirty = Object.keys(draft).length > 0;

  const credentials = fields.filter((field) => field.section === primarySection);
  const tuning = fields.filter((field) => field.section !== primarySection);

  const handleSave = () => {
    const changes: Partial<Record<SettingsSection, Record<string, unknown>>> = {};
    for (const field of fields) {
      if (field.key in draft) {
        changes[field.section] = { ...changes[field.section], [field.key]: draft[field.key] };
      }
    }
    update.mutate(changes, { onSuccess: onClose });
  };

  const renderField = (field: SettingFieldInfo) => (
    <SettingsField
      key={field.key}
      field={field}
      value={valueFor(field.key)}
      options={optionsFor(field)}
      onChange={(value) => setDraft((prev) => ({ ...prev, [field.key]: value }))}
    />
  );

  return (
    <ResponsiveModal opened onClose={onClose} title={t(labelKeyFor(integration))}>
      <Stack gap="md">
        {credentials.map(renderField)}

        {tuning.length > 0 && (
          <>
            <Divider
              my="xs"
              labelPosition="left"
              label={
                <Text size="xs" fw={700} c="dimmed" tt="uppercase">
                  {t('settings.services.advanced')}
                </Text>
              }
            />
            {tuning.map(renderField)}
          </>
        )}

        <Group justify="space-between" mt="sm">
          <Button
            variant="light"
            loading={test.isPending}
            onClick={() =>
              test.mutate({ integration, payload: connectionTestPayload(integration, draft) })
            }
          >
            {t('settings.test.action')}
          </Button>
          <Group gap="xs">
            <Button variant="subtle" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleSave} disabled={!dirty} loading={update.isPending}>
              {t('common.save')}
            </Button>
          </Group>
        </Group>
      </Stack>
    </ResponsiveModal>
  );
}
