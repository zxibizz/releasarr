import { Container, Group, Stack, Tabs } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { accessibleSystemItems } from '@/navigation';

/** The system area: a tab per operational view, each gated by its own permission. */
export function SystemLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();

  const visible = accessibleSystemItems(hasPermission);
  const active = visible.find((item) => pathname.startsWith(item.to))?.to ?? visible[0]?.to;

  return (
    <Container size="lg" className="safe-area-inline">
      <Stack gap="md">
        {/* Below sm the burger drawer carries these links instead; a tab strip
            that narrow could only scroll sideways. */}
        <Tabs
          visibleFrom="sm"
          value={active}
          onChange={(value) => {
            if (value) {
              void navigate(value);
            }
          }}
        >
          <Tabs.List style={{ flexWrap: 'nowrap', overflowX: 'auto' }} aria-label={t('system.nav.label')}>
            {visible.map((item) => (
              <Tabs.Tab key={item.to} value={item.to}>
                <Group gap={6} wrap="nowrap">
                  {t(item.labelKey)}
                  {item.badge?.()}
                </Group>
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
        <Outlet />
      </Stack>
    </Container>
  );
}

/** Bare `/system` has no page of its own: land on the first one this caller can reach. */
export function SystemIndexRedirect() {
  const { hasPermission } = useAuth();
  const first = accessibleSystemItems(hasPermission)[0];
  return <Navigate to={first?.to ?? '/'} replace />;
}
