import { ActionIcon, Box, Group, Stack, Text, TextInput, Tooltip } from '@mantine/core';
import { modals } from '@mantine/modals';
import { IconCopy, IconRefresh } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import { Panel } from '@/components/Panel';
import { useRegenerateServiceKey, useServiceKey } from '@/features/users/queries';

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
      <Text fz="lg" fw={700}>
        {t('serviceKey.title')}
      </Text>
      <Text size="sm" c="dimmed">
        {t('serviceKey.description')}
      </Text>

      {!isLoading && key ? (
        <Panel>
          <Box p="md">
            <TextInput
              label={t('serviceKey.label')}
              value={key.key}
              readOnly
              styles={{ input: { fontFamily: 'monospace' } }}
              rightSectionWidth={64}
              rightSectionPointerEvents="all"
              rightSection={
                <Group gap={4} wrap="nowrap">
                  <Tooltip label={t('serviceKey.copy')}>
                    <ActionIcon
                      variant="subtle"
                      aria-label={t('serviceKey.copy')}
                      onClick={() => void navigator.clipboard?.writeText(key.key)}
                    >
                      <IconCopy size={16} />
                    </ActionIcon>
                  </Tooltip>
                  <Tooltip label={t('serviceKey.regenerate.action')}>
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      aria-label={t('serviceKey.regenerate.action')}
                      loading={regenerate.isPending}
                      onClick={confirmRegenerate}
                    >
                      <IconRefresh size={16} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              }
            />
          </Box>
        </Panel>
      ) : null}
    </Stack>
  );
}
