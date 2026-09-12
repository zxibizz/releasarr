import { Paper } from '@mantine/core';
import type { ReactNode } from 'react';

import { useIsMobile } from '@/hooks/useIsMobile';

/**
 * Frames a table. On a phone the table is rendered as bordered cards instead, so
 * the panel drops its own border to avoid a border inside a border.
 */
export function Panel({ children }: { children: ReactNode }) {
  const isMobile = useIsMobile();

  return (
    <Paper withBorder={!isMobile} radius="lg" p={0}>
      {children}
    </Paper>
  );
}
