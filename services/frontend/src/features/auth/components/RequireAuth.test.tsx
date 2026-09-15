import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { RequireAuth } from '@/features/auth/components/RequireAuth';
import type { AuthContextValue } from '@/features/auth/context';
import { renderWithProviders } from '@/test/utils';

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

  it('redirects to /setup when no admin exists yet', () => {
    renderGuarded({ status: 'setup-required' });
    expect(screen.getByText('Setup page')).toBeInTheDocument();
  });
});
