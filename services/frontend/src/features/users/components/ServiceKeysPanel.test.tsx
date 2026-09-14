import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ServiceKeysPanel } from '@/features/users/components/ServiceKeysPanel';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { ServiceApiKeyInfo } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const existingKey: ServiceApiKeyInfo = {
  prefix: 'rlsr_abcdef',
  last_used_at: null,
  created_at: '2026-01-01T00:00:00Z',
};

describe('ServiceKeysPanel', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('shows the current key prefix', async () => {
    vi.mocked(apiRequest).mockResolvedValue(existingKey as never);

    renderWithProviders(<ServiceKeysPanel />);

    expect(await screen.findByText('rlsr_abcdef…')).toBeInTheDocument();
  });

  it('regenerates the key and shows the plaintext exactly once, only after confirming', async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string, options = {}) => {
      if (path === '/service-key/regenerate' && options.method === 'POST') {
        return {
          key: { prefix: 'rlsr_fedcba', last_used_at: null, created_at: '2026-01-02T00:00:00Z' },
          plaintext: 'rlsr_supersecretvalue',
        } as never;
      }
      return existingKey as never;
    });

    renderWithProviders(<ServiceKeysPanel />);
    await screen.findByText('rlsr_abcdef…');

    await userEvent.click(screen.getByRole('button', { name: 'Regenerate' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Regenerate' }));

    expect(await screen.findByText('rlsr_supersecretvalue')).toBeInTheDocument();
    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/service-key/regenerate', { method: 'POST' }),
    );
  });
});
