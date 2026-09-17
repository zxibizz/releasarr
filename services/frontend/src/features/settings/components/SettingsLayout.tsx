import { Container, Stack, Tabs } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { SETTINGS_ITEMS } from '@/navigation';

/** The settings area: a tab per section, admin-only. */
export function SettingsLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const visible = isAdmin ? SETTINGS_ITEMS : [];
  const active = visible.find((section) => pathname.startsWith(section.to))?.to ?? visible[0]?.to;

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
