import { Paper, Stack, Text, Title } from '@mantine/core';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: string;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <Paper withBorder radius="lg" p="xl" bg="dark.7">
      <Stack align="center" gap="xs" py="xl">
        <Text fz={40} lh={1}>
          {icon}
        </Text>
        <Title order={4}>{title}</Title>
        {description && (
          <Text c="dimmed" size="sm" ta="center" maw={460}>
            {description}
          </Text>
        )}
        {action}
      </Stack>
    </Paper>
  );
}
