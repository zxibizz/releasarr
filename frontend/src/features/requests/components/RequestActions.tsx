import { Card, SimpleGrid, Stack, Text, UnstyledButton } from '@mantine/core';

export interface RequestAction {
  key: string;
  icon: string;
  title: string;
  description: string;
  onClick: () => void;
  loading?: boolean;
}

interface RequestActionsProps {
  actions: RequestAction[];
}

export function RequestActions({ actions }: RequestActionsProps) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
      {actions.map((action) => (
        <UnstyledButton
          key={action.key}
          onClick={action.onClick}
          disabled={action.loading}
          style={{ opacity: action.loading ? 0.6 : 1 }}
        >
          <Card withBorder radius="lg" padding="md" h="100%">
            <Stack gap={4}>
              <Text fz={22} lh={1}>
                {action.icon}
              </Text>
              <Text fw={600}>{action.title}</Text>
              <Text size="sm" c="dimmed">
                {action.description}
              </Text>
            </Stack>
          </Card>
        </UnstyledButton>
      ))}
    </SimpleGrid>
  );
}
