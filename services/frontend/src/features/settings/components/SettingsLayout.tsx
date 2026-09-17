import { Container, NavLink, ScrollArea, Select, Stack } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { useIsMobile } from '@/hooks/useIsMobile';

interface SettingsSectionDef {
  to: string;
  labelKey: string;
  /** Settings is admin-only except the users section, which manage_users reaches. */
  adminOnly: boolean;
}

// Order here is the sidebar order.
const SECTIONS: SettingsSectionDef[] = [
  { to: '/settings/general', labelKey: 'settings.nav.general', adminOnly: true },
  { to: '/settings/users', labelKey: 'settings.nav.users', adminOnly: false },
  { to: '/settings/services', labelKey: 'settings.nav.services', adminOnly: true },
  { to: '/settings/metadata', labelKey: 'settings.nav.metadata', adminOnly: true },
  { to: '/settings/network', labelKey: 'settings.nav.network', adminOnly: true },
  { to: '/settings/tasks', labelKey: 'settings.nav.tasks', adminOnly: true },
  { to: '/settings/logging', labelKey: 'settings.nav.logging', adminOnly: true },
];

/**
 * The settings area: a section list on the left (a select on a phone) with the
 * active section rendered beside it. Visible to admins in full; a user holding
 * only `manage_users` sees the users section and nothing else.
 */
export function SettingsLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isAdmin, hasPermission } = useAuth();
  const isMobile = useIsMobile();

  const visible = SECTIONS.filter(
    (section) => isAdmin || (!section.adminOnly && hasPermission('manage_users')),
  );

  const active = visible.find((section) => pathname.startsWith(section.to)) ?? visible[0];

  return (
    <Container size="lg" className="safe-area-inline">
      <Stack gap="md">
        {isMobile ? (
          <Select
            aria-label={t('settings.nav.label')}
            value={active?.to}
            data={visible.map((section) => ({ value: section.to, label: t(section.labelKey) }))}
            onChange={(value) => {
              if (value) {
                void navigate(value);
              }
            }}
          />
        ) : (
          <div style={{ display: 'flex', gap: 'var(--mantine-spacing-lg)', alignItems: 'flex-start' }}>
            <ScrollArea w={220} component="nav" aria-label={t('settings.nav.label')}>
              <Stack gap={4}>
                {visible.map((section) => (
                  <NavLink
                    key={section.to}
                    label={t(section.labelKey)}
                    active={pathname.startsWith(section.to)}
                    onClick={() => void navigate(section.to)}
                  />
                ))}
              </Stack>
            </ScrollArea>
            <div style={{ flex: 1, minWidth: 0 }}>
              <Outlet />
            </div>
          </div>
        )}
        {isMobile && <Outlet />}
      </Stack>
    </Container>
  );
}
