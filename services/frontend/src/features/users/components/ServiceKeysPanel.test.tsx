import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ServiceKeysPanel } from '@/features/users/components/ServiceKeysPanel';
import { apiRequest } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';
import type { ServiceApiKey } from '@/types';

vi.mock('@/lib/api/client', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/client')>('@/lib/api/client');
  return { ...actual, apiRequest: vi.fn() };
});

const existingKey: ServiceApiKey = {
  key: 'rlsr_abcdef1234567890',
  last_used_at: null,
  created_at: '2026-01-01T00:00:00Z',
};

describe('ServiceKeysPanel', () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it('shows the current key value in a readonly field', async () => {
    vi.mocked(apiRequest).mockResolvedValue(existingKey as never);

    renderWithProviders(<ServiceKeysPanel />);

    const input = await screen.findByLabelText<HTMLInputElement>(/^key/i);
    expect(input).toHaveValue('rlsr_abcdef1234567890');
    expect(input).toHaveAttribute('readonly');
  });

  it('regenerates the key only after confirming, and shows the new value', async () => {
    let current = existingKey;
    vi.mocked(apiRequest).mockImplementation(async (path: string, options = {}) => {
      if (path === '/service-key/regenerate' && options.method === 'POST') {
        current = {
          key: 'rlsr_fedcba0987654321',
          last_used_at: null,
          created_at: '2026-01-02T00:00:00Z',
        };
        return current as never;
      }
      return current as never;
    });

    renderWithProviders(<ServiceKeysPanel />);
    await screen.findByDisplayValue('rlsr_abcdef1234567890');

    await userEvent.click(screen.getByRole('button', { name: 'Regenerate' }));
    const dialog = await screen.findByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Regenerate' }));

    expect(await screen.findByDisplayValue('rlsr_fedcba0987654321')).toBeInTheDocument();
    await waitFor(() =>
      expect(apiRequest).toHaveBeenCalledWith('/service-key/regenerate', { method: 'POST' }),
    );
  });
});
