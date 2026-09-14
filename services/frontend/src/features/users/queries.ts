import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { usersApi } from '@/features/users/api';
import { getErrorMessage } from '@/utils/errors';
import type { CreateUserPayload, UpdateUserPayload } from '@/types';

export const userKeys = {
  all: ['users'] as const,
  list: () => [...userKeys.all, 'list'] as const,
};

export const usersListQuery = () => ({
  queryKey: userKeys.list(),
  queryFn: ({ signal }: { signal: AbortSignal }) => usersApi.list(signal),
});

export function useUsersList(options: { enabled?: boolean } = {}) {
  const query = useQuery({ ...usersListQuery(), enabled: options.enabled ?? true });
  return { ...query, users: query.data?.users ?? [] };
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateUserPayload) => usersApi.create(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.list() });
      notifications.show({ message: 'User created', color: 'teal' });
    },
    onError: (error: unknown) => {
      notifications.show({ title: 'Could not create user', message: getErrorMessage(error, ''), color: 'red' });
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateUserPayload }) =>
      usersApi.update(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.list() });
      notifications.show({ message: 'User updated', color: 'teal' });
    },
    onError: (error: unknown) => {
      notifications.show({ title: 'Could not update user', message: getErrorMessage(error, ''), color: 'red' });
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.remove(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: userKeys.list() });
      notifications.show({ message: 'User deleted', color: 'teal' });
    },
    onError: (error: unknown) => {
      notifications.show({ title: 'Could not delete user', message: getErrorMessage(error, ''), color: 'red' });
    },
  });
}
