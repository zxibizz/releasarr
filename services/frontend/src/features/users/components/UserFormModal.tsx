import { Button, Checkbox, Modal, PasswordInput, Select, Stack, Text, TextInput } from '@mantine/core';
import { type FormEvent, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useRootFolders } from '@/features/discover/queries';
import { useCreateUser, useUpdateUser } from '@/features/users/queries';
import type { User } from '@/types';

interface UserFormModalProps {
  opened: boolean;
  onClose: () => void;
  /** Present when editing; absent when creating a new user. */
  user?: User | null;
}

export function UserFormModal({ opened, onClose, user }: UserFormModalProps) {
  const { t } = useTranslation();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const isEditing = Boolean(user);

  const [username, setUsername] = useState(user?.username ?? '');
  const [displayName, setDisplayName] = useState(user?.display_name ?? '');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'user'>(user?.role ?? 'user');
  const [isActive, setIsActive] = useState(user?.is_active ?? true);
  const [canViewAllRequests, setCanViewAllRequests] = useState(user?.can_view_all_requests ?? false);
  const [canAccessTasks, setCanAccessTasks] = useState(user?.can_access_tasks ?? false);
  const [canAccessIndexers, setCanAccessIndexers] = useState(user?.can_access_indexers ?? false);
  const [canAccessLogs, setCanAccessLogs] = useState(user?.can_access_logs ?? false);
  const [allowedRootFolders, setAllowedRootFolders] = useState<string[]>(
    user?.allowed_root_folders ?? [],
  );

  // Sonarr and Radarr each expose their own root folders, but a user's
  // allow-list is a single flat set of paths shared by both (see
  // allowed_root_folders() on the backend).
  const seriesFolders = useRootFolders('series', { enabled: opened });
  const movieFolders = useRootFolders('movie', { enabled: opened });
  const knownPaths = useMemo(() => {
    const paths = new Set<string>();
    for (const folder of seriesFolders.data?.folders ?? []) {
      paths.add(folder.path);
    }
    for (const folder of movieFolders.data?.folders ?? []) {
      paths.add(folder.path);
    }
    return paths;
  }, [seriesFolders.data, movieFolders.data]);
  // A path once granted but no longer reported by either *arr still needs to
  // be shown (grayed out) so it can be unchecked, not just silently dropped.
  const displayedPaths = useMemo(() => {
    const paths = new Set(knownPaths);
    for (const path of allowedRootFolders) {
      paths.add(path);
    }
    return Array.from(paths).sort();
  }, [knownPaths, allowedRootFolders]);

  const toggleFolder = (path: string, checked: boolean) => {
    setAllowedRootFolders((current) =>
      checked ? [...current, path] : current.filter((p) => p !== path),
    );
  };

  const pending = createUser.isPending || updateUser.isPending;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (isEditing && user) {
      await updateUser.mutateAsync({
        id: user.id,
        payload: {
          display_name: displayName || null,
          ...(password ? { password } : {}),
          role,
          is_active: isActive,
          can_view_all_requests: canViewAllRequests,
          can_access_tasks: canAccessTasks,
          can_access_indexers: canAccessIndexers,
          can_access_logs: canAccessLogs,
          allowed_root_folders: allowedRootFolders,
        },
      });
    } else {
      await createUser.mutateAsync({
        username,
        password,
        display_name: displayName || undefined,
        role,
        is_active: isActive,
        can_view_all_requests: canViewAllRequests,
        can_access_tasks: canAccessTasks,
        can_access_indexers: canAccessIndexers,
        can_access_logs: canAccessLogs,
        allowed_root_folders: allowedRootFolders,
      });
    }
    onClose();
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={isEditing ? t('users.form.editTitle') : t('users.form.createTitle')}
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          <TextInput
            label={t('users.form.username')}
            required
            disabled={isEditing}
            value={username}
            onChange={(event) => setUsername(event.currentTarget.value)}
          />
          <TextInput
            label={t('users.form.displayName')}
            value={displayName ?? ''}
            onChange={(event) => setDisplayName(event.currentTarget.value)}
          />
          <PasswordInput
            label={isEditing ? t('users.form.newPassword') : t('users.form.password')}
            required={!isEditing}
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
          />
          <Select
            label={t('users.form.role')}
            data={[
              { value: 'admin', label: t('users.roles.admin') },
              { value: 'user', label: t('users.roles.user') },
            ]}
            value={role}
            onChange={(value) => setRole((value as 'admin' | 'user') ?? 'user')}
            allowDeselect={false}
          />
          <Checkbox
            label={t('users.form.isActive')}
            checked={isActive}
            onChange={(event) => setIsActive(event.currentTarget.checked)}
          />
          <Checkbox
            label={t('users.form.canViewAllRequests')}
            checked={canViewAllRequests}
            onChange={(event) => setCanViewAllRequests(event.currentTarget.checked)}
          />
          <Checkbox
            label={t('users.form.canAccessTasks')}
            checked={canAccessTasks}
            onChange={(event) => setCanAccessTasks(event.currentTarget.checked)}
          />
          <Checkbox
            label={t('users.form.canAccessIndexers')}
            checked={canAccessIndexers}
            onChange={(event) => setCanAccessIndexers(event.currentTarget.checked)}
          />
          <Checkbox
            label={t('users.form.canAccessLogs')}
            checked={canAccessLogs}
            onChange={(event) => setCanAccessLogs(event.currentTarget.checked)}
          />
          <Stack gap={4}>
            <Text size="sm" fw={500}>
              {t('users.form.allowedRootFolders')}
            </Text>
            <Text size="xs" c="dimmed">
              {t('users.form.allowedRootFoldersHint')}
            </Text>
            {displayedPaths.length === 0 ? (
              <Text size="sm" c="dimmed">
                {t('users.form.allowedRootFoldersEmpty')}
              </Text>
            ) : (
              displayedPaths.map((path) => (
                <Checkbox
                  key={path}
                  label={
                    <Text size="sm" c={knownPaths.has(path) ? undefined : 'dimmed'}>
                      {path}
                    </Text>
                  }
                  checked={allowedRootFolders.includes(path)}
                  onChange={(event) => toggleFolder(path, event.currentTarget.checked)}
                />
              ))
            )}
          </Stack>
          <Button type="submit" loading={pending}>
            {t('common.save')}
          </Button>
        </Stack>
      </form>
    </Modal>
  );
}
