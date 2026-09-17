import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SystemIndexRedirect, SystemLayout } from '@/features/system/components/SystemLayout';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders, TEST_ADMIN_USER } from '@/test/utils';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const restrictedAuth = (permission: string | null) => ({
  isAdmin: false,
  user: { ...TEST_ADMIN_USER, role: 'user' as const },
  hasPermission: (candidate: string) => candidate === permission,
});

function renderLayout(route: string, options?: Parameters<typeof renderWithProviders>[1]) {
  return renderWithProviders(
    <Routes>
      <Route path="/" element={<p>requests page</p>} />
      <Route path="/system" element={<SystemLayout />}>
        <Route index element={<SystemIndexRedirect />} />
        <Route path="tasks" element={<p>tasks page</p>} />
        <Route path="indexers" element={<p>indexers page</p>} />
        <Route path="logs" element={<p>logs page</p>} />
        <Route path="users" element={<p>users page</p>} />
      </Route>
    </Routes>,
    { route, ...options },
  );
}

beforeEach(() => {
  vi.mocked(apiRequest).mockReset();
  vi.mocked(apiRequest).mockResolvedValue([]);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('SystemLayout', () => {
  it('offers a tab per system page an admin can reach', () => {
    renderLayout('/system/tasks');

    const tabs = within(screen.getByRole('tablist')).getAllByRole('tab');
    expect(tabs.map((tab) => tab.textContent)).toEqual(['Tasks', 'Indexers', 'Logs', 'Users']);
    expect(screen.getByRole('tab', { name: 'Tasks' })).toHaveAttribute('aria-selected', 'true');
  });

  it('navigates to the section a tab names', async () => {
    const user = userEvent.setup();
    renderLayout('/system/tasks');

    await user.click(screen.getByRole('tab', { name: 'Logs' }));

    expect(await screen.findByText('logs page')).toBeInTheDocument();
  });

  it('hides the tab strip below sm, where the drawer carries the same links', () => {
    renderLayout('/system/tasks');

    expect(screen.getByRole('tablist').closest('.mantine-visible-from-sm')).not.toBeNull();
  });

  it('omits the sections a restricted user has no permission for', () => {
    renderLayout('/system/logs', { auth: restrictedAuth('logs') });

    const tabs = within(screen.getByRole('tablist')).getAllByRole('tab');
    expect(tabs.map((tab) => tab.textContent)).toEqual(['Logs']);
  });
});

describe('SystemIndexRedirect', () => {
  it('lands on the first page the caller can reach', async () => {
    renderLayout('/system', { auth: restrictedAuth('logs') });

    expect(await screen.findByText('logs page')).toBeInTheDocument();
  });

  it('falls back to the requests list when no system page is reachable', async () => {
    renderLayout('/system', { auth: restrictedAuth(null) });

    expect(await screen.findByText('requests page')).toBeInTheDocument();
  });
});
