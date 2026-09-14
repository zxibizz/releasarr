import { ActionIcon, Alert, Badge, Button, Group, Stack, Text } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconCopy } from '@tabler/icons-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Panel } from '@/components/Panel';
import { useRegenerateServiceKey, useServiceKey } from '@/features/users/queries';
import { formatDateTime } from '@/utils/formatters';

/** Admin-only view of the single, always-present service API key (for the bot and similar integrations). */
export function ServiceKeysPanel() {
  const { t } = useTranslation();
  const { data: key, isLoading } = useServiceKey();
  const regenerate = useRegenerateServiceKey();
  const [plaintext, setPlaintext] = useState<string | null>(null);

  const confirmRegenerate = () => {
    modals.openConfirmModal({
      title: t('serviceKey.regenerate.title'),
      children: <Text size="sm">{t('serviceKey.regenerate.body')}</Text>,
      labels: { confirm: t('serviceKey.regenerate.action'), cancel: t('common.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: async () => {
        const result = await regenerate.mutateAsync();
        setPlaintext(result.plaintext);
      },
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
          <Group justify="space-between">
            <Group gap="xs">
              <Text ff="monospace" size="sm">
                {key.prefix}…
              </Text>
              <Badge variant="light" color="grape">
                {t('serviceKey.alwaysAdmin')}
              </Badge>
            </Group>
            <Text size="xs" c="dimmed">
              {key.last_used_at
                ? t('serviceKey.lastUsed', { date: formatDateTime(key.last_used_at) })
                : t('serviceKey.neverUsed')}
            </Text>
          </Group>
        </Panel>
      ) : null}

      {plaintext ? (
        <Alert
          color="yellow"
          variant="light"
          withCloseButton
          title={t('serviceKey.onlyShownOnce')}
          onClose={() => setPlaintext(null)}
        >
          <Group gap="xs" wrap="nowrap" align="flex-start">
            <Text ff="monospace" size="sm" style={{ wordBreak: 'break-all', flex: 1 }}>
              {plaintext}
            </Text>
            <ActionIcon
              variant="light"
              aria-label={t('serviceKey.copy')}
              onClick={() => void navigator.clipboard?.writeText(plaintext)}
            >
              <IconCopy size={16} />
            </ActionIcon>
          </Group>
        </Alert>
      ) : null}
    </Stack>
  );
}
