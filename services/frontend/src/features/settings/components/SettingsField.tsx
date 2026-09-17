import { Badge, Group, NumberInput, Switch, TagsInput, Text, TextInput, Tooltip } from '@mantine/core';
import { IconLock } from '@tabler/icons-react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { SettingFieldInfo } from '@/types';

interface SettingsFieldProps {
  field: SettingFieldInfo;
  value: unknown;
  onChange: (value: unknown) => void;
}

/**
 * One editable setting. Renders the right control for the field's kind, plus a
 * lock badge when the environment pins it (making it read-only) and a restart
 * note when a change only takes effect on the next boot.
 */
export function SettingsField({ field, value, onChange }: SettingsFieldProps) {
  const { t } = useTranslation();
  const label = t(`settings.fields.${field.key}.label`, { defaultValue: field.key });
  const description = t(`settings.fields.${field.key}.description`, { defaultValue: '' });
  const descriptionProp = description === '' ? undefined : description;

  const suffix = (
    <Group gap={6} wrap="nowrap">
      {field.locked && (
        <Tooltip label={t('settings.lockedTooltip')}>
          <Badge
            color="gray"
            variant="light"
            leftSection={<IconLock size={12} />}
            aria-label={t('settings.locked')}
          >
            {t('settings.locked')}
          </Badge>
        </Tooltip>
      )}
      {field.requires_restart && !field.locked && (
        <Tooltip label={t('settings.restartTooltip')}>
          <Badge color="yellow" variant="light">
            {t('settings.restart')}
          </Badge>
        </Tooltip>
      )}
    </Group>
  );

  const common = {
    label: label as ReactNode,
    description: descriptionProp,
    disabled: field.locked,
    rightSection: suffix,
  };

  switch (field.kind) {
    case 'bool':
      return (
        <Group justify="space-between" wrap="nowrap">
          <div>
            <Text size="sm" fw={500}>
              {label}
            </Text>
            {descriptionProp && (
              <Text size="xs" c="dimmed">
                {descriptionProp}
              </Text>
            )}
          </div>
          <Group gap="xs" wrap="nowrap">
            {suffix}
            <Switch
              aria-label={label}
              checked={Boolean(value)}
              disabled={field.locked}
              onChange={(event) => onChange(event.currentTarget.checked)}
            />
          </Group>
        </Group>
      );
    case 'int':
    case 'int_optional':
      return (
        <NumberInput
          {...common}
          value={typeof value === 'number' ? value : ((value as number | null) ?? undefined)}
          allowDecimal={false}
          onChange={(v) => onChange(v === '' || v == null ? null : Number(v))}
        />
      );
    case 'float':
      return (
        <NumberInput
          {...common}
          value={typeof value === 'number' ? value : undefined}
          decimalScale={2}
          onChange={(v) => onChange(v === '' || v == null ? null : Number(v))}
        />
      );
    case 'str_list':
      return (
        <TagsInput
          label={label}
          description={descriptionProp}
          disabled={field.locked}
          value={Array.isArray(value) ? (value as string[]) : []}
          onChange={(v) => onChange(v)}
          rightSection={suffix}
        />
      );
    case 'str':
    case 'str_optional':
    default:
      return (
        <TextInput
          {...common}
          type={field.is_secret ? 'password' : 'text'}
          value={value == null ? '' : String(value)}
          onChange={(event) => onChange(event.currentTarget.value || (field.kind === 'str_optional' ? null : ''))}
          autoComplete="off"
        />
      );
  }
}
