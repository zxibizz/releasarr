import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { LoginPage } from '@/features/auth/pages/LoginPage';
import { ApiError } from '@/lib/api/client';
import { renderWithProviders } from '@/test/utils';

const login = vi.fn();

vi.mock('@/features/auth/AuthProvider', async () => {
  const actual = await vi.importActual<typeof import('@/features/auth/AuthProvider')>(
    '@/features/auth/AuthProvider',
  );
  return { ...actual, useAuth: () => ({ login }) };
});

const navigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigate,
    useLocation: () => ({ pathname: '/login', search: '', state: null }),
  };
});

describe('LoginPage', () => {
  it('logs in and navigates to the requested page', async () => {
    login.mockResolvedValueOnce(undefined);
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/^username/i), 'alice');
    await userEvent.type(screen.getByLabelText(/^password/i), 'hunter2');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => expect(login).toHaveBeenCalledWith('alice', 'hunter2', false));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/', { replace: true }));
  });

  it('shows an error for the wrong password', async () => {
    login.mockRejectedValueOnce(new ApiError('Invalid', { status: 401 }));
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/^username/i), 'alice');
    await userEvent.type(screen.getByLabelText(/^password/i), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Incorrect username or password.')).toBeInTheDocument();
  });

  it('shows a locked-out message after too many failed attempts', async () => {
    login.mockRejectedValueOnce(new ApiError('Locked', { status: 423 }));
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/^username/i), 'alice');
    await userEvent.type(screen.getByLabelText(/^password/i), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Too many failed attempts. Try again later.')).toBeInTheDocument();
  });

  it('checks remember me through to the login call', async () => {
    login.mockResolvedValueOnce(undefined);
    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByLabelText(/^username/i), 'alice');
    await userEvent.type(screen.getByLabelText(/^password/i), 'hunter2');
    await userEvent.click(screen.getByLabelText('Remember me'));
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => expect(login).toHaveBeenCalledWith('alice', 'hunter2', true));
  });
});
