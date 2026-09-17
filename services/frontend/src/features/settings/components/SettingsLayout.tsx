import { Container, Stack, Tabs } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';

interface SettingsSectionDef {
  to: string;
  labelKey: string;
}

// Order here is the tab order.
const SECTIONS: SettingsSectionDef[] = [
  { to: '/settings/general', labelKey: 'settings.nav.general' },
  { to: '/settings/services', labelKey: 'settings.nav.services' },
  { to: '/settings/metadata', labelKey: 'settings.nav.metadata' },
  { to: '/settings/network', labelKey: 'settings.nav.network' },
  { to: '/settings/tasks', labelKey: 'settings.nav.tasks' },
  { to: '/settings/logging', labelKey: 'settings.nav.logging' },
];

/** The settings area: a tab per section, admin-only. */
export function SettingsLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const visible = isAdmin ? SECTIONS : [];
  const active = visible.find((section) => pathname.startsWith(section.to))?.to ?? visible[0]?.to;

  return (
    <Container size="lg" className="safe-area-inline">
      <Stack gap="md">
        <Tabs
          value={active}
          onChange={(value) => {
            if (value) {
              void navigate(value);
            }
          }}
        >
          <Tabs.List style={{ flexWrap: 'nowrap', overflowX: 'auto' }} aria-label={t('settings.nav.label')}>
            {visible.map((section) => (
              <Tabs.Tab key={section.to} value={section.to}>
                {t(section.labelKey)}
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs>
        <Outlet />
      </Stack>
    </Container>
  );
}
