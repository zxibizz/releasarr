import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Route, Routes } from 'react-router-dom';

import { RequirePermission } from '@/features/auth/components/RequirePermission';
import type { AuthContextValue } from '@/features/auth/context';
import { renderWithProviders } from '@/test/utils';

function renderGuarded(auth: Partial<AuthContextValue>) {
  return renderWithProviders(
    <Routes>
      <Route element={<RequirePermission permission="tasks" />}>
        <Route path="/tasks" element={<div>Tasks content</div>} />
      </Route>
      <Route path="/" element={<div>Home page</div>} />
    </Routes>,
    { auth, route: '/tasks' },
  );
}

describe('RequirePermission', () => {
  it('renders the route when the permission is granted', () => {
    renderGuarded({ hasPermission: () => true });
    expect(screen.getByText('Tasks content')).toBeInTheDocument();
  });

  it('redirects home when the permission is missing', () => {
    renderGuarded({ hasPermission: () => false });
    expect(screen.getByText('Home page')).toBeInTheDocument();
  });
});
