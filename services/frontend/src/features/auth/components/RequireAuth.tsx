import { Center, Loader } from '@mantine/core';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/features/auth/AuthProvider';

/** Gates every route behind an authenticated session, or sends the visitor to set one up. */
export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();

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

  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
