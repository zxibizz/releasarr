import { Navigate, Outlet } from 'react-router-dom';

import type { Permission } from '@/features/auth/permissions';
import { useAuth } from '@/features/auth/useAuth';

/** Gates a route subtree behind a specific permission flag (admins always pass). */
export function RequirePermission({ permission }: { permission: Permission }) {
  const { hasPermission } = useAuth();

  if (!hasPermission(permission)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
