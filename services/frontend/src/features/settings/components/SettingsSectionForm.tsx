import { Button, Center, Group, Loader, Stack, Text, Title } from '@mantine/core';
import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { SettingsField } from '@/features/settings/components/SettingsField';
import { useSettings, useUpdateSettingsSection } from '@/features/settings/queries';
import type { SettingFieldInfo, SettingsSection } from '@/types';

interface SettingsSectionFormProps {
  section: SettingsSection;
  titleKey: string;
  descriptionKey?: string;
  /** Render extra controls (e.g. connection-test buttons) inside the form. */
  children?: ReactNode;
}

/**
 * A section of the settings: every editable field for it, a save button that
 * lights up once something changed, and the shared locked/restart affordances.
 * Values are a flat key→value map; the server composes them with the
 * environment layer.
 */
export function SettingsSectionForm({
  section,
  titleKey,
  descriptionKey,
  children,
}: SettingsSectionFormProps) {
  const { t } = useTranslation();
  const settings = useSettings();

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

  // Remount on section change so the draft resets rather than syncing via an
  // effect; each section edits an independent key set.
  return (
    <SectionFormBody
      key={section}
      section={section}
      titleKey={titleKey}
      descriptionKey={descriptionKey}
      values={settings.data.values[section] ?? {}}
      fields={(settings.data.fields ?? []).filter((f: SettingFieldInfo) => f.section === section)}
    >
      {children}
    </SectionFormBody>
  );
}

interface SectionFormBodyProps {
  section: SettingsSection;
  titleKey: string;
  descriptionKey?: string;
  values: Record<string, unknown>;
  fields: SettingFieldInfo[];
  children?: ReactNode;
}

function SectionFormBody({
  section,
  titleKey,
  descriptionKey,
  values,
  fields,
  children,
}: SectionFormBodyProps) {
  const { t } = useTranslation();
  const update = useUpdateSettingsSection();
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const valueFor = (key: string) => (key in draft ? draft[key] : values[key]);
  const dirty = Object.keys(draft).length > 0;

  const handleSave = () => {
    update.mutate(
      { section, values: draft },
      { onSuccess: () => setDraft({}) },
    );
  };

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>{t(titleKey)}</Title>
        {descriptionKey && (
          <Text c="dimmed" size="sm" mt={4}>
            {t(descriptionKey)}
          </Text>
        )}
      </div>

      <Stack gap="md">
        {fields.map((field) => (
          <SettingsField
            key={field.key}
            field={field}
            value={valueFor(field.key)}
            onChange={(value) => setDraft((prev) => ({ ...prev, [field.key]: value }))}
          />
        ))}
      </Stack>

      {children}

      <Group justify="flex-end">
        <Button onClick={handleSave} disabled={!dirty} loading={update.isPending}>
          {t('common.save')}
        </Button>
      </Group>
    </Stack>
  );
}
