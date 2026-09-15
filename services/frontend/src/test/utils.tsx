import { MantineProvider } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';

import { AuthContext, type AuthContextValue } from '@/features/auth/context';
import '@/lib/i18n';
import { theme } from '@/theme';
import type { SessionUser } from '@/types';

/** Roughly an iPhone 14 in CSS pixels. */
export const MOBILE_WIDTH = 390;
export const DESKTOP_WIDTH = 1280;

/**
 * Answers `max-width` media queries as if the viewport were `width` wide, so the
 * phone and desktop branches of a component can both be rendered under jsdom,
 * which has no layout of its own.
 *
 * Reduced motion is reported as preferred, which is true of jsdom in the sense
 * that matters: it runs no animation frames to finish a transition with, so
 * without this, components that mount their content on `transitionend` would
 * never reveal it.
 */
export function setViewportWidth(width: number) {
  window.matchMedia = ((query: string) => {
    const maxWidthEm = /\(max-width:\s*([\d.]+)em\)/.exec(query);

    const matches = query.includes('prefers-reduced-motion')
      ? true
      : maxWidthEm
        ? width <= Number.parseFloat(maxWidthEm[1]) * 16
        : false;

    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    };
  }) as unknown as typeof window.matchMedia;
}

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

/**
 * Defaults every test to an authenticated, unrestricted admin — the same
 * stance the old single-API-key world had — so tests that don't care about
 * auth don't have to think about it. Pass `auth` to `renderWithProviders` to
 * exercise a restricted user or a specific permission set instead.
 */
export const TEST_ADMIN_USER: SessionUser = {
  id: 'test-admin',
  username: 'admin',
  display_name: 'Test Admin',
  role: 'admin',
  is_active: true,
  can_view_all_requests: true,
  can_access_tasks: true,
  can_access_indexers: true,
  can_access_logs: true,
  allowed_root_folders: [],
  last_login_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export const TEST_AUTH_VALUE: AuthContextValue = {
  status: 'authenticated',
  user: TEST_ADMIN_USER,
  isAdmin: true,
  hasPermission: () => true,
  login: async () => {},
  completeSetup: async () => {},
  logout: async () => {},
};

export function renderWithProviders(
  ui: ReactElement,
  {
    route = '/',
    auth,
    ...options
  }: RenderOptions & { route?: string; auth?: Partial<AuthContextValue> } = {},
) {
  const queryClient = createTestQueryClient();
  const authValue: AuthContextValue = { ...TEST_AUTH_VALUE, ...auth };

  // Mirrors the providers main.tsx mounts, so a component that opens a confirm
  // dialog through the modals manager has somewhere to render it.
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <MantineProvider theme={theme} forceColorScheme="dark" env="test">
      <QueryClientProvider client={queryClient}>
        <ModalsProvider>
          <AuthContext.Provider value={authValue}>
            <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
          </AuthContext.Provider>
        </ModalsProvider>
      </QueryClientProvider>
    </MantineProvider>
  );

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...options }) };
}
