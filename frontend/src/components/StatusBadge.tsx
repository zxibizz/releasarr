import { Badge } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { getStatusPresentation } from '@/utils/status';

interface StatusBadgeProps {
  status: string;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  withIcon?: boolean;
}

export function StatusBadge({ status, size = 'sm', withIcon = true }: StatusBadgeProps) {
  const { t } = useTranslation();
  const { color, icon } = getStatusPresentation(status);
  const label = t(`status.${status}`, { defaultValue: status });

  return (
    <Badge color={color} variant="light" size={size} radius="sm">
      {withIcon ? `${icon} ${label}` : label}
    </Badge>
  );
}
