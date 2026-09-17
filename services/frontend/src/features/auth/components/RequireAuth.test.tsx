import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { RequireAuth } from '@/features/auth/components/RequireAuth';
import type { AuthContextValue } from '@/features/auth/context';
import { renderWithProviders, setOnlineStatus } from '@/test/utils';

function renderGuarded(auth: Partial<AuthContextValue>) {
  return renderWithProviders(
    <Routes>
      <Route element={<RequireAuth />}>
        <Route index element={<div>Protected content</div>} />
      </Route>
      <Route path="/login" element={<div>Login page</div>} />
      <Route path="/setup" element={<div>Setup page</div>} />
    </Routes>,
    { auth },
  );
}

describe('RequireAuth', () => {
  afterEach(() => setOnlineStatus(true));

  it('shows a loader while the session is being resolved', () => {
    renderGuarded({ status: 'loading' });
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument();
  });

  it('renders the protected route once authenticated', () => {
    renderGuarded({ status: 'authenticated' });
    expect(screen.getByText('Protected content')).toBeInTheDocument();
  });

  it('redirects to /login when there is no session', () => {
    renderGuarded({ status: 'anonymous' });
    expect(screen.getByText('Login page')).toBeInTheDocument();
  });

  it('reports the connection instead of offering a sign-in it cannot submit', () => {
    setOnlineStatus(false);

    renderGuarded({ status: 'anonymous' });

    expect(screen.queryByText('Login page')).not.toBeInTheDocument();
    expect(screen.getByText('Cannot reach Releasarr')).toBeInTheDocument();
  });

  it('offers a retry instead of a sign-in when the server itself is down', () => {
    renderGuarded({ status: 'unavailable' });

    expect(screen.queryByText('Login page')).not.toBeInTheDocument();
    expect(screen.getByText('Releasarr is unavailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument();
  });

  it('redirects to /setup when no admin exists yet', () => {
    renderGuarded({ status: 'setup-required' });
    expect(screen.getByText('Setup page')).toBeInTheDocument();
  });
});
