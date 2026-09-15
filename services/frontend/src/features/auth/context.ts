import { createContext } from 'react';

import type { Permission } from '@/features/auth/permissions';
import type { SessionUser } from '@/types';

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
