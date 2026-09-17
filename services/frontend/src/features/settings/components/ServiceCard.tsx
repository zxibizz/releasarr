import { Badge, Button, Card, Group, Stack, Text } from '@mantine/core';
import { IconPencil } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

import type { ServiceIntegration } from '@/features/settings/serviceFields';

interface ServiceCardProps {
  integration: ServiceIntegration;
  url: string;
  configured: boolean;
  testing: boolean;
  onTest: () => void;
  onEdit: () => void;
}

/** One external service, summarised: where it points and whether it is usable. */
export function ServiceCard({
  integration,
  url,
  configured,
  testing,
  onTest,
  onEdit,
}: ServiceCardProps) {
  const { t } = useTranslation();
  const name = t(`settings.services.${integration}`);

  return (
    <Card withBorder radius="md" padding="md">
      <Stack gap="sm" h="100%">
        <Group justify="space-between" wrap="nowrap" align="flex-start">
          <Text fw={600}>{name}</Text>
          <Badge variant="light" color={configured ? 'teal' : 'gray'}>
            {t(configured ? 'settings.services.configured' : 'settings.services.notConfigured')}
          </Badge>
        </Group>

        <Text size="sm" c="dimmed" className="break-anywhere">
          {url || t('settings.services.noUrl')}
        </Text>

        <Group gap="xs" mt="auto">
          <Button size="xs" variant="light" loading={testing} onClick={onTest}>
            {t('settings.test.action')}
          </Button>
          <Button
            size="xs"
            variant="subtle"
            leftSection={<IconPencil size={14} />}
            onClick={onEdit}
            aria-label={t('settings.services.editService', { name })}
          >
            {t('common.edit')}
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}
