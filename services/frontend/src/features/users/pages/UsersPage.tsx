import { Badge, Button, Group, Table, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { Panel } from '@/components/Panel';
import { ServiceKeysPanel } from '@/features/users/components/ServiceKeysPanel';
import { UserFormModal } from '@/features/users/components/UserFormModal';
import { useDeleteUser, useUsersList } from '@/features/users/queries';
import type { User } from '@/types';

export function UsersPage() {
  const { t } = useTranslation();
  const { users, isLoading } = useUsersList();
  const deleteUser = useDeleteUser();
  const [formOpened, formModal] = useDisclosure(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  // Forces UserFormModal to remount on every open — Mantine keeps it mounted
  // between opens, so its useState initializers would otherwise never re-run
  // for the newly selected user.
  const [formKey, setFormKey] = useState(0);

  const openCreate = () => {
    setEditingUser(null);
    setFormKey((key) => key + 1);
    formModal.open();
  };

  const openEdit = (user: User) => {
    setEditingUser(user);
    setFormKey((key) => key + 1);
    formModal.open();
  };

  const confirmDelete = (user: User) => {
    modals.openConfirmModal({
      title: t('users.delete.title'),
      children: <Text size="sm">{t('users.delete.body', { username: user.username })}</Text>,
      labels: { confirm: t('users.delete.confirm'), cancel: t('common.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => deleteUser.mutate(user.id),
    });
  };

  if (!isLoading && users.length === 0) {
    return (
      <EmptyState
        icon="👤"
        title={t('users.empty.title')}
        description={t('users.empty.description')}
        action={<Button onClick={openCreate}>{t('users.newUser')}</Button>}
      />
    );
  }

  return (
    <>
      <Group justify="space-between" mb="md">
        <Text fz="xl" fw={700}>
          {t('users.title')}
        </Text>
        <Button onClick={openCreate}>{t('users.newUser')}</Button>
      </Group>

      <Panel>
        <Table.ScrollContainer minWidth={640}>
          <Table verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t('users.form.username')}</Table.Th>
                <Table.Th>{t('users.form.role')}</Table.Th>
                <Table.Th>{t('users.columns.status')}</Table.Th>
                <Table.Th>{t('users.columns.permissions')}</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {users.map((user) => (
                <Table.Tr key={user.id}>
                  <Table.Td>
                    <Text fw={600}>{user.display_name || user.username}</Text>
                    <Text size="xs" c="dimmed">
                      {user.username}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={user.role === 'admin' ? 'grape' : 'gray'} variant="light">
                      {t(`users.roles.${user.role}`)}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={user.is_active ? 'teal' : 'red'} variant="light">
                      {user.is_active ? t('users.columns.active') : t('users.columns.inactive')}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap={4}>
                      {user.role === 'admin' ? (
                        <Text size="xs" c="dimmed">
                          {t('users.columns.allPermissions')}
                        </Text>
                      ) : (
                        [
                          user.can_view_all_requests && t('permissions.viewAllRequests'),
                          user.can_access_tasks && t('nav.tasks'),
                          user.can_access_indexers && t('nav.indexers'),
                          user.can_access_logs && t('nav.logs'),
                        ]
                          .filter(Boolean)
                          .map((label) => (
                            <Badge key={label as string} variant="default" size="sm">
                              {label}
                            </Badge>
                          ))
                      )}
                    </Group>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" justify="flex-end">
                      <Button variant="subtle" size="xs" onClick={() => openEdit(user)}>
                        {t('common.edit')}
                      </Button>
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        onClick={() => confirmDelete(user)}
                      >
                        {t('common.delete')}
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Panel>

      <ServiceKeysPanel />

      <UserFormModal key={formKey} opened={formOpened} onClose={formModal.close} user={editingUser} />
    </>
  );
}
