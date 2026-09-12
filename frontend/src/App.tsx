import { AppShell, Container, Group, Text, UnstyledButton } from '@mantine/core';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { LanguageSwitcher } from '@/components/LanguageSwitcher';

function Navigation() {
  const { t } = useTranslation();
  const location = useLocation();
  const isRequestsActive =
    location.pathname === '/' || location.pathname.startsWith('/request');

  return (
    <Container size="lg" h="100%">
      <Group h="100%" justify="space-between" wrap="nowrap">
        <UnstyledButton component={Link} to="/">
          <Text
            fz="xl"
            fw={700}
            variant="gradient"
            gradient={{ from: 'blue', to: 'grape', deg: 135 }}
          >
            Releasarr
          </Text>
        </UnstyledButton>

        <Group gap="lg" wrap="nowrap">
          <Text
            component={Link}
            to="/"
            size="sm"
            fw={600}
            c={isRequestsActive ? 'blue.4' : 'dimmed'}
            style={{ textDecoration: 'none' }}
          >
            {t('nav.requests')}
          </Text>
          <LanguageSwitcher />
        </Group>
      </Group>
    </Container>
  );
}

export function AppLayout() {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, [location.pathname, location.search]);

  return (
    <AppShell header={{ height: 64 }} padding="md">
      <AppShell.Header
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <Navigation />
      </AppShell.Header>

      <AppShell.Main>
        <Container size="lg" py="xl">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}

export default AppLayout;
