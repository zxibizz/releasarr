import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { authApi } from '@/features/auth/api';
import { AuthContext, type AuthContextValue, type AuthStatus } from '@/features/auth/context';
import { userHasPermission } from '@/features/auth/permissions';
import { onAuthExpired, refreshSession, setAccessToken } from '@/lib/api/client';
import { queryClient } from '@/lib/queryClient';
import type { SessionUser } from '@/types';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<SessionUser | null>(null);

  // Runs once: is there anyone to create, and failing that, does a remembered
  // session still exist behind the (httpOnly, invisible-to-JS) refresh cookie.
  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const setup = await authApi.setupStatus();
        if (setup.required) {
          if (!cancelled) {
            setStatus('setup-required');
          }
          return;
        }
      } catch {
        // A failed setup-status check should not itself block trying a session.
      }

      // Restoring the session is the API client's job, not this component's:
      // the bootstrap and any request that 401s share one in-flight refresh,
      // so the second pass React StrictMode makes here joins the first rather
      // than asking the server to rotate the same cookie twice.
      const session = await refreshSession();
      if (cancelled) {
        return;
      }
      if (session) {
        setUser(session.user);
        setStatus('authenticated');
      } else {
        setStatus('anonymous');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(
    () =>
      onAuthExpired(() => {
        // Whatever is cached (root folders, requests, ...) was fetched under
        // the now-invalid session and must not be served to whoever logs in
        // next in this tab.
        queryClient.clear();
        setUser(null);
        setStatus('anonymous');
      }),
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      isAdmin: user?.role === 'admin',
      hasPermission: (permission) => userHasPermission(user, permission),
      login: async (username, password, rememberMe) => {
        const session = await authApi.login({
          username,
          password,
          remember_me: rememberMe,
        });
        setAccessToken(session.access_token);
        setUser(session.user);
        setStatus('authenticated');
      },
      completeSetup: async (username, password, displayName) => {
        const session = await authApi.completeSetup({
          username,
          password,
          display_name: displayName || undefined,
        });
        setAccessToken(session.access_token);
        setUser(session.user);
        setStatus('authenticated');
      },
      logout: async () => {
        try {
          await authApi.logout();
        } finally {
          setAccessToken(null);
          setUser(null);
          setStatus('anonymous');
          // Otherwise the next login in this tab would see this user's
          // cached responses (e.g. an admin's unrestricted root folders)
          // before its own queries land.
          queryClient.clear();
        }
      },
    }),
    [status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
