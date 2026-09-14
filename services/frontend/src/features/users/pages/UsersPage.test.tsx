import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiRequest } from '@/lib/api/client';
import { UsersPage } from '@/features/users/pages/UsersPage';
import { renderWithProviders } from '@/test/utils';
import type { User } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const admin: User = {
  id: 'u-admin',
  username: 'admin',
  display_name: 'Admin',
  role: 'admin',
  is_active: true,
  can_view_all_requests: true,
  can_access_tasks: true,
  can_access_indexers: true,
  can_access_logs: true,
  allowed_root_folders: [],
  last_login_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const restricted: User = {
  id: 'u-restricted',
  username: 'viewer',
  display_name: 'Restricted Viewer',
  role: 'user',
  is_active: true,
  can_view_all_requests: false,
  can_access_tasks: false,
  can_access_indexers: false,
  can_access_logs: false,
  allowed_root_folders: ['/media/movies'],
  last_login_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('UsersPage', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('lists every user with their role and permissions', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ users: [admin, restricted] } as never);

    renderWithProviders(<UsersPage />);

    expect(await screen.findByText('admin')).toBeInTheDocument();
    expect(screen.getByText('viewer')).toBeInTheDocument();
    expect(screen.getByText('All (admin)')).toBeInTheDocument();
  });

  it('creates a user through the form modal', async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string, options = {}) => {
      if (path === '/users' && options.method === 'POST') {
        return { ...restricted, username: 'newuser' } as never;
      }
      return { users: [admin] } as never;
    });

    renderWithProviders(<UsersPage />);
    await screen.findByText('admin');

    await userEvent.click(screen.getByRole('button', { name: 'New user' }));
    await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());
    await userEvent.type(screen.getByLabelText(/^username/i), 'newuser');
    await userEvent.type(screen.getByLabelText(/^password/i), 'a-long-password');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(
        '/users',
        expect.objectContaining({
          method: 'POST',
          body: expect.objectContaining({ username: 'newuser' }),
        }),
      ),
    );
  });

  it('deletes a user only once the confirmation dialog is accepted', async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string, options = {}) => {
      if (path === `/users/${restricted.id}` && options.method === 'DELETE') {
        return undefined as never;
      }
      return { users: [admin, restricted] } as never;
    });

    renderWithProviders(<UsersPage />);
    await screen.findByText('viewer');

    const rows = screen.getAllByRole('row');
    const viewerRow = rows.find((row) => row.textContent?.includes('viewer'));
    expect(viewerRow).toBeDefined();
    await userEvent.click(
      Array.from(viewerRow!.querySelectorAll('button')).find(
        (button) => button.textContent === 'Delete',
      )!,
    );

    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(`/users/${restricted.id}`, { method: 'DELETE' }),
    );
  });
});
