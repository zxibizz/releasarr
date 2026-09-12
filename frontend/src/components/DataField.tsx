import { Box, Group, Text } from '@mantine/core';
import type { ReactNode } from 'react';

interface DataFieldProps {
  label: string;
  children: ReactNode;
}

/**
 * One label/value pair, used to restate a table row as a stacked card on narrow
 * screens where a real table would only be reachable by scrolling sideways.
 */
export function DataField({ label, children }: DataFieldProps) {
  return (
    <Group justify="space-between" align="flex-start" gap="md" wrap="nowrap">
      <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Box ta="right" style={{ minWidth: 0 }}>
        {children}
      </Box>
    </Group>
  );
}
