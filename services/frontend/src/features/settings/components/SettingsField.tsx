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

  const badges = (
    <>
      {field.locked && (
        <Tooltip label={t('settings.lockedTooltip')}>
          <Badge
            color="gray"
            variant="light"
            size="sm"
            leftSection={<IconLock size={12} />}
            aria-label={t('settings.locked')}
          >
            {t('settings.locked')}
          </Badge>
        </Tooltip>
      )}
      {field.requires_restart && !field.locked && (
        <Tooltip label={t('settings.restartTooltip')}>
          <Badge color="yellow" variant="light" size="sm">
            {t('settings.restart')}
          </Badge>
        </Tooltip>
      )}
    </>
  );

  // The badges sit in the label rather than in the input's rightSection: that
  // section is a fixed, input-height square, so a badge rendered there is
  // clipped to its icon and overlaps the value.
  const labelWithBadges = (
    <Group component="span" display="inline-flex" gap={6} wrap="nowrap" align="center">
      <span>{label}</span>
      {badges}
    </Group>
  ) as ReactNode;

  const common = {
    label: labelWithBadges,
    description: descriptionProp,
    disabled: field.locked,
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
            {badges}
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
          label={labelWithBadges}
          description={descriptionProp}
          disabled={field.locked}
          value={Array.isArray(value) ? (value as string[]) : []}
          onChange={(v) => onChange(v)}
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
