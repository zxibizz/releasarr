import { Modal, Text } from '@mantine/core';
import type { ReactNode } from 'react';

import { useIsMobile } from '@/hooks/useIsMobile';

interface ResponsiveModalProps {
  opened: boolean;
  onClose: () => void;
  /** Rendered truncated to two lines, so a long release name cannot push the close button away. */
  title: string;
  children: ReactNode;
}

/**
 * A centred dialog on desktop, full screen on a phone. A phone has no room for
 * a floating panel: the padding and backdrop eat the width the content needs.
 */
export function ResponsiveModal({ opened, onClose, title, children }: ResponsiveModalProps) {
  const isMobile = useIsMobile();

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      fullScreen={isMobile}
      padding={isMobile ? 'sm' : 'md'}
      title={
        <Text fw={600} lineClamp={2} className="break-anywhere">
          {title}
        </Text>
      }
    >
      {children}
    </Modal>
  );
}
