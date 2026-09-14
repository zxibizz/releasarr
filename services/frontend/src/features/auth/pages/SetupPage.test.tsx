import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SetupPage } from '@/features/auth/pages/SetupPage';
import { renderWithProviders } from '@/test/utils';

const completeSetup = vi.fn();

vi.mock('@/features/auth/AuthProvider', async () => {
  const actual = await vi.importActual<typeof import('@/features/auth/AuthProvider')>(
    '@/features/auth/AuthProvider',
  );
  return { ...actual, useAuth: () => ({ completeSetup }) };
});

const navigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => navigate };
});

describe('SetupPage', () => {
  it('rejects a blank username without calling the backend', async () => {
    renderWithProviders(<SetupPage />);

    await userEvent.type(screen.getByLabelText('Password'), 'a-long-password');
    await userEvent.click(screen.getByRole('button', { name: 'Create admin account' }));

    expect(await screen.findByText('A username is required.')).toBeInTheDocument();
    expect(completeSetup).not.toHaveBeenCalled();
  });

  it('rejects a short password without calling the backend', async () => {
    renderWithProviders(<SetupPage />);

    await userEvent.type(screen.getByLabelText('Username'), 'root');
    await userEvent.type(screen.getByLabelText('Password'), 'short');
    await userEvent.click(screen.getByRole('button', { name: 'Create admin account' }));

    expect(
      await screen.findByText('Password must be at least 8 characters.'),
    ).toBeInTheDocument();
    expect(completeSetup).not.toHaveBeenCalled();
  });

  it('creates the admin account and redirects home', async () => {
    completeSetup.mockResolvedValueOnce(undefined);
    renderWithProviders(<SetupPage />);

    await userEvent.type(screen.getByLabelText('Username'), 'root');
    await userEvent.type(screen.getByLabelText('Password'), 'a-long-password');
    await userEvent.click(screen.getByRole('button', { name: 'Create admin account' }));

    await waitFor(() =>
      expect(completeSetup).toHaveBeenCalledWith('root', 'a-long-password', ''),
    );
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/', { replace: true }));
  });

  it('shows an error when the backend refuses to create the account', async () => {
    completeSetup.mockRejectedValueOnce(new Error('setup already complete'));
    renderWithProviders(<SetupPage />);

    await userEvent.type(screen.getByLabelText('Username'), 'root');
    await userEvent.type(screen.getByLabelText('Password'), 'a-long-password');
    await userEvent.click(screen.getByRole('button', { name: 'Create admin account' }));

    expect(
      await screen.findByText('Could not create the admin account. Please try again.'),
    ).toBeInTheDocument();
  });
});
