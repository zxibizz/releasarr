import type { SessionUser } from '@/types';

export type Permission = 'view_all_requests' | 'tasks' | 'indexers' | 'logs' | 'manage_users';

/** Mirrors the backend's Permission model: admin bypasses every flag. */
export function userHasPermission(user: SessionUser | null, permission: Permission): boolean {
  if (!user) {
    return false;
  }
  if (user.role === 'admin') {
    return true;
  }
  switch (permission) {
    case 'view_all_requests':
      return user.can_view_all_requests;
    case 'tasks':
      return user.can_access_tasks;
    case 'indexers':
      return user.can_access_indexers;
    case 'logs':
      return user.can_access_logs;
    case 'manage_users':
      return false;
    default:
      return false;
  }
}
