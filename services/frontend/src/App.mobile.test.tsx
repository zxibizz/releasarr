import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppLayout } from '@/App';
import { apiRequest } from '@/lib/api/client';
import {
  DESKTOP_WIDTH,
  MOBILE_WIDTH,
  renderWithProviders,
  setViewportWidth,
  TEST_ADMIN_USER,
} from '@/test/utils';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const restrictedAuth = (permission: string | null) => ({
  isAdmin: false,
  user: { ...TEST_ADMIN_USER, role: 'user' as const },
  hasPermission: (candidate: string) => candidate === permission,
});

async function openDrawer(auth?: ReturnType<typeof restrictedAuth>) {
  const user = userEvent.setup();
  renderWithProviders(<AppLayout />, { auth });

  await user.click(screen.getByRole('button', { name: /open navigation menu/i }));
  // Scoped to the nav rather than the panel, whose title is a link to the home page.
  return within(within(await screen.findByRole('dialog')).getByRole('navigation'));
}

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockResolvedValue([]);
  setViewportWidth(MOBILE_WIDTH);
});

afterEach(() => {
  setViewportWidth(DESKTOP_WIDTH);
  vi.clearAllMocks();
});

/**
 * The header collapses Settings and System to a single link each, and below sm
 * neither area renders its tab strip, so the drawer is the only way to reach a
 * sub-page on a phone.
 */
describe('the mobile navigation drawer', () => {
  it('lists every settings and system sub-page an admin can reach', async () => {
    const drawer = await openDrawer();

    expect(drawer.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/',
      '/add',
      '/settings/general',
      '/settings/services',
      '/settings/metadata',
      '/settings/network',
      '/settings/tasks',
      '/settings/logging',
      '/system/tasks',
      '/system/indexers',
      '/system/logs',
      '/system/users',
    ]);
    expect(drawer.getByText('Settings')).toBeInTheDocument();
    expect(drawer.getByText('System')).toBeInTheDocument();
  });

  it('withholds settings from a non-admin and system pages they cannot reach', async () => {
    const drawer = await openDrawer(restrictedAuth('logs'));

    expect(drawer.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/',
      '/add',
      '/system/logs',
    ]);
    expect(drawer.queryByText('Settings')).not.toBeInTheDocument();
  });

  it('drops both groups entirely for a user with no system access', async () => {
    const drawer = await openDrawer(restrictedAuth(null));

    expect(drawer.getAllByRole('link').map((link) => link.getAttribute('href'))).toEqual([
      '/',
      '/add',
    ]);
    expect(drawer.queryByText('System')).not.toBeInTheDocument();
  });

  it('marks the open sub-page as the current one', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppLayout />, { route: '/settings/network' });

    await user.click(screen.getByRole('button', { name: /open navigation menu/i }));
    const drawer = within(await screen.findByRole('dialog'));

    expect(drawer.getByRole('link', { name: 'Network' })).toHaveAttribute('aria-current', 'page');
  });
});
