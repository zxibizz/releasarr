import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ServiceKeysPanel } from '@/features/users/components/ServiceKeysPanel';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { ServiceApiKey, User } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const bot: User = {
  id: 'u-bot',
  username: 'bot',
  display_name: 'Bot Account',
  role: 'user',
  is_active: true,
  can_view_all_requests: false,
  can_access_tasks: false,
  can_access_indexers: false,
  can_access_logs: false,
  allowed_root_folders: [],
  last_login_at: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const existingKey: ServiceApiKey = {
  id: 'key-1',
  name: 'Existing key',
  prefix: 'rlsr_abcdef',
  user_id: bot.id,
  can_impersonate: false,
  is_active: true,
  expires_at: null,
  last_used_at: null,
  created_at: '2026-01-01T00:00:00Z',
};

describe('ServiceKeysPanel', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('lists existing keys by name and the user they act as', async () => {
    vi.mocked(apiRequest).mockResolvedValue({ service_keys: [existingKey] } as never);

    renderWithProviders(<ServiceKeysPanel users={[bot]} />);

    expect(await screen.findByText('Existing key')).toBeInTheDocument();
    expect(screen.getByText('bot')).toBeInTheDocument();
  });

  it('creates a key and shows the plaintext exactly once', async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string, options = {}) => {
      if (path === '/service-keys' && options.method === 'POST') {
        return {
          key: { ...existingKey, id: 'key-2', name: 'Bot key' },
          plaintext: 'rlsr_supersecretvalue',
        } as never;
      }
      return { service_keys: [] } as never;
    });

    renderWithProviders(<ServiceKeysPanel users={[bot]} />);
    await screen.findByText('No service keys yet.');

    await userEvent.click(screen.getByRole('button', { name: 'New key' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.type(within(dialog).getByLabelText(/^name/i), 'Bot key');
    await userEvent.click(within(dialog).getByRole('combobox', { name: /^acts as/i }));
    await userEvent.click(await screen.findByRole('option', { name: 'bot' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save' }));

    expect(await screen.findByText('rlsr_supersecretvalue')).toBeInTheDocument();
    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(
        '/service-keys',
        expect.objectContaining({
          method: 'POST',
          body: expect.objectContaining({ name: 'Bot key', user_id: 'u-bot' }),
        }),
      ),
    );
  });

  it('revokes a key only once confirmed', async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string, options = {}) => {
      if (path === `/service-keys/${existingKey.id}` && options.method === 'DELETE') {
        return undefined as never;
      }
      return { service_keys: [existingKey] } as never;
    });

    renderWithProviders(<ServiceKeysPanel users={[bot]} />);
    await screen.findByText('Existing key');

    await userEvent.click(screen.getByRole('button', { name: 'Revoke' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Revoke' }));

    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith(`/service-keys/${existingKey.id}`, {
        method: 'DELETE',
      }),
    );
  });
});
