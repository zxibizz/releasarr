import {
  AppShell,
  Burger,
  Container,
  Divider,
  Drawer,
  Group,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation } from 'react-router-dom';

import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { useSyncWatcher } from '@/features/tasks/queries';

interface NavItem {
  to: string;
  labelKey: string;
  isActive: (pathname: string) => boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    labelKey: 'nav.requests',
    isActive: (pathname) => pathname === '/' || pathname.startsWith('/request'),
  },
  {
    to: '/system/tasks',
    labelKey: 'nav.system',
    isActive: (pathname) => pathname.startsWith('/system'),
  },
];

function Logo() {
  return (
    <UnstyledButton component={Link} to="/">
      <Text fz="xl" fw={700} variant="gradient" gradient={{ from: 'blue', to: 'grape', deg: 135 }}>
        Releasarr
      </Text>
    </UnstyledButton>
  );
}

function Navigation({ onOpenMenu, menuOpened }: { onOpenMenu: () => void; menuOpened: boolean }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  return (
    <Container size="lg" h="100%" className="safe-area-inline">
      <Group h="100%" justify="space-between" wrap="nowrap" gap="sm">
        <Logo />

        <Group component="nav" gap="lg" wrap="nowrap" visibleFrom="sm">
          {NAV_ITEMS.map((item) => {
            const active = item.isActive(pathname);
            return (
              <Text
                key={item.to}
                component={Link}
                to={item.to}
                size="sm"
                fw={600}
                c={active ? 'blue.4' : 'dimmed'}
                aria-current={active ? 'page' : undefined}
                style={{ textDecoration: 'none' }}
              >
                {t(item.labelKey)}
              </Text>
            );
          })}
          <LanguageSwitcher />
        </Group>

        <Burger
          opened={menuOpened}
          onClick={onOpenMenu}
          hiddenFrom="sm"
          size="sm"
          aria-label={t('nav.openMenu')}
        />
      </Group>
    </Container>
  );
}

function MobileMenu({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="80%"
      title={<Logo />}
      hiddenFrom="sm"
      zIndex={300}
    >
      <Stack gap="xs" component="nav">
        {NAV_ITEMS.map((item) => {
          const active = item.isActive(pathname);
          return (
            <UnstyledButton
              key={item.to}
              component={Link}
              to={item.to}
              onClick={onClose}
              aria-current={active ? 'page' : undefined}
              px="md"
              py="sm"
              style={{
                borderRadius: 'var(--mantine-radius-md)',
                backgroundColor: active ? 'var(--mantine-color-dark-6)' : undefined,
              }}
            >
              <Text fw={600} c={active ? 'blue.4' : undefined}>
                {t(item.labelKey)}
              </Text>
            </UnstyledButton>
          );
        })}

        <Divider my="sm" />

        <Stack gap={6} px="md">
          <Text size="xs" c="dimmed" tt="uppercase">
            {t('nav.languageLabel')}
          </Text>
          <LanguageSwitcher size="sm" w="100%" />
        </Stack>
      </Stack>
    </Drawer>
  );
}

export function AppLayout() {
  const location = useLocation();
  // Destructured because `useDisclosure` returns a new handlers object on every
  // render; depending on the whole object would re-close the menu as it opens.
  const [menuOpened, { close: closeMenu, toggle: toggleMenu }] = useDisclosure(false);

  // Watched here rather than on the tasks page so a sync finishing still
  // refreshes request and release data wherever the user happens to be.
  useSyncWatcher();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    closeMenu();
  }, [location.pathname, location.search, closeMenu]);

  return (
    <AppShell header={{ height: { base: 56, sm: 64 } }} padding={{ base: 'xs', sm: 'md' }}>
      <AppShell.Header
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <Navigation menuOpened={menuOpened} onOpenMenu={toggleMenu} />
      </AppShell.Header>

      <MobileMenu opened={menuOpened} onClose={closeMenu} />

      <AppShell.Main>
        <Container size="lg" py={{ base: 'md', sm: 'xl' }} className="safe-area-bottom">
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}

export default AppLayout;
