import { Badge, Group, Select, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/features/auth/AuthProvider';
import { useUpdateRequestOwner } from '@/features/requests/queries';
import { useUsersList } from '@/features/users/queries';
import type { MediaRequest } from '@/types';

/**
 * Shows who a request belongs to, and — for an admin — a control to reassign
 * it. A plain badge, not `StatusBadge`: that component is for lifecycle status
 * only, not for arbitrary per-user colors.
 */
export function RequestOwner({ request }: { request: MediaRequest }) {
  const { t } = useTranslation();
  const { isAdmin, user } = useAuth();
  const { users } = useUsersList({ enabled: isAdmin });
  const updateOwner = useUpdateRequestOwner(request.id);

  if (!isAdmin) {
    // A restricted viewer only ever sees their own requests, so there is
    // nothing to resolve here beyond their own name, already in context.
    const label = request.owner_user_id === user?.id ? user?.username : t('requestPage.owner.unowned');
    return (
      <Group gap={6}>
        <Text size="sm" c="dimmed">
          {t('requestPage.owner.label')}
        </Text>
        <Badge variant="light" color="gray">
          {label}
        </Badge>
      </Group>
    );
  }

  return (
    <Group gap={6} wrap="nowrap">
      <Text size="sm" c="dimmed">
        {t('requestPage.owner.label')}
      </Text>
      <Select
        size="xs"
        w={200}
        placeholder={t('requestPage.owner.unowned')}
        clearable
        data={users.map((user) => ({ value: user.id, label: user.username }))}
        value={request.owner_user_id ?? null}
        onChange={(value) => updateOwner.mutate(value)}
        disabled={updateOwner.isPending}
      />
    </Group>
  );
}
