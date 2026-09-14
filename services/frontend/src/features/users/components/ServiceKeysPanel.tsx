import { ActionIcon, Badge, Button, Group, Stack, Text, TextInput } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconCopy } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { Panel } from '@/components/Panel';
import { useRegenerateServiceKey, useServiceKey } from '@/features/users/queries';
import { formatDateTime } from '@/utils/formatters';

/** Admin-only view of the single, always-present service API key (for the bot and similar integrations). */
export function ServiceKeysPanel() {
  const { t } = useTranslation();
  const { data: key, isLoading } = useServiceKey();
  const regenerate = useRegenerateServiceKey();

  const confirmRegenerate = () => {
    modals.openConfirmModal({
      title: t('serviceKey.regenerate.title'),
      children: <Text size="sm">{t('serviceKey.regenerate.body')}</Text>,
      labels: { confirm: t('serviceKey.regenerate.action'), cancel: t('common.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => regenerate.mutate(),
    });
  };

  return (
    <Stack gap="sm" mt="xl">
      <Group justify="space-between">
        <Text fz="lg" fw={700}>
          {t('serviceKey.title')}
        </Text>
        <Button
          variant="light"
          color="red"
          onClick={confirmRegenerate}
          loading={regenerate.isPending}
        >
          {t('serviceKey.regenerate.action')}
        </Button>
      </Group>
      <Text size="sm" c="dimmed">
        {t('serviceKey.description')}
      </Text>

      {!isLoading && key ? (
        <Panel>
          <Stack gap="xs">
            <TextInput
              label={t('serviceKey.label')}
              value={key.key}
              readOnly
              styles={{ input: { fontFamily: 'monospace' } }}
              rightSection={
                <ActionIcon
                  variant="subtle"
                  aria-label={t('serviceKey.copy')}
                  onClick={() => void navigator.clipboard?.writeText(key.key)}
                >
                  <IconCopy size={16} />
                </ActionIcon>
              }
            />
            <Group justify="space-between">
              <Badge variant="light" color="grape">
                {t('serviceKey.alwaysAdmin')}
              </Badge>
              <Text size="xs" c="dimmed">
                {key.last_used_at
                  ? t('serviceKey.lastUsed', { date: formatDateTime(key.last_used_at) })
                  : t('serviceKey.neverUsed')}
              </Text>
            </Group>
          </Stack>
        </Panel>
      ) : null}
    </Stack>
  );
}
