import { Center, Loader } from '@mantine/core';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { OfflineState } from '@/components/OfflineState';
import { ServerUnavailable } from '@/components/ServerUnavailable';
import { useAuth } from '@/features/auth/useAuth';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';

/** Gates every route behind an authenticated session, or sends the visitor to set one up. */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  const isOnline = useOnlineStatus();

  if (status === 'loading') {
    return (
      <Center mih="60vh">
        <Loader />
      </Center>
    );
  }

  if (status === 'setup-required') {
    return <Navigate to="/setup" replace />;
  }

  /*
   * The bootstrap got a 5xx from the server itself: the session may be fine,
   * and a sign-in form would hit the same dead backend, so offer a retry that
   * re-runs the bootstrap instead.
   */
  if (status === 'unavailable') {
    return (
      <Center mih="60vh" p="xl">
        <ServerUnavailable />
      </Center>
    );
  }

  if (status === 'anonymous') {
    /*
     * Offline, a bootstrap that found no session is indistinguishable from one
     * that could not ask — the refresh call never left the machine. Redirecting
     * to a sign-in form that cannot submit would be worse than saying so.
     */
    if (!isOnline) {
      return (
        <Center mih="60vh" p="xl">
          <OfflineState />
        </Center>
      );
    }

    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
