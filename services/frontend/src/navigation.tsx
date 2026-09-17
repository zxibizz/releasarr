import type { ReactNode } from 'react';

import type { Permission } from '@/features/auth/permissions';
import { IndexerAlertBadge } from '@/features/indexers/components/IndexerAlertBadge';

export interface NavItem {
  to: string;
  labelKey: string;
  isActive: (pathname: string) => boolean;
  /** Hidden unless the signed-in user has this permission (admins always see it). */
  permission?: Permission;
  /** Rendered beside the label, for items that can demand attention. */
  badge?: () => ReactNode;
}

export const PRIMARY_ITEMS: NavItem[] = [
  {
    to: '/',
    labelKey: 'nav.requests',
    isActive: (pathname) => pathname === '/' || pathname.startsWith('/request'),
  },
  {
    to: '/add',
    labelKey: 'nav.add',
    isActive: (pathname) => pathname.startsWith('/add'),
  },
];

// Settings is configuration (admin-only); System is operational views, in the
// priority order a caller lands on first when neither has its own sub-nav.
export const SETTINGS_ITEMS: NavItem[] = [
  { to: '/settings/general', labelKey: 'settings.nav.general', isActive: (p) => p.startsWith('/settings/general') },
  { to: '/settings/services', labelKey: 'settings.nav.services', isActive: (p) => p.startsWith('/settings/services') },
  { to: '/settings/metadata', labelKey: 'settings.nav.metadata', isActive: (p) => p.startsWith('/settings/metadata') },
  { to: '/settings/network', labelKey: 'settings.nav.network', isActive: (p) => p.startsWith('/settings/network') },
  { to: '/settings/tasks', labelKey: 'settings.nav.tasks', isActive: (p) => p.startsWith('/settings/tasks') },
  { to: '/settings/logging', labelKey: 'settings.nav.logging', isActive: (p) => p.startsWith('/settings/logging') },
];

export const SYSTEM_ITEMS: NavItem[] = [
  { to: '/system/tasks', labelKey: 'nav.tasks', isActive: (p) => p.startsWith('/system/tasks'), permission: 'tasks' },
  { to: '/system/indexers', labelKey: 'nav.indexers', isActive: (p) => p.startsWith('/system/indexers'), permission: 'indexers', badge: () => <IndexerAlertBadge /> },
  { to: '/system/logs', labelKey: 'nav.logs', isActive: (p) => p.startsWith('/system/logs'), permission: 'logs' },
  { to: '/system/users', labelKey: 'nav.users', isActive: (p) => p.startsWith('/system/users'), permission: 'manage_users' },
];

export function accessibleSystemItems(hasPermission: (permission: Permission) => boolean): NavItem[] {
  return SYSTEM_ITEMS.filter((item) => !item.permission || hasPermission(item.permission));
}
