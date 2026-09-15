import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { authApi } from '@/features/auth/api';
import { onAuthExpired, refreshSession, setAccessToken } from '@/lib/api/client';
import { queryClient } from '@/lib/queryClient';
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

export type AuthStatus = 'loading' | 'setup-required' | 'anonymous' | 'authenticated';

export interface AuthContextValue {
  status: AuthStatus;
  user: SessionUser | null;
  isAdmin: boolean;
  hasPermission: (permission: Permission) => boolean;
  login: (username: string, password: string, rememberMe: boolean) => Promise<void>;
  completeSetup: (username: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

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

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
