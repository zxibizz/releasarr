import {
  AppShell,
  Avatar,
  Burger,
  Container,
  Divider,
  Drawer,
  Group,
  Menu,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { type ReactNode, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import type { Permission } from '@/features/auth/permissions';
import { useAuth } from '@/features/auth/useAuth';
import { IndexerAlertBadge } from '@/features/indexers/components/IndexerAlertBadge';
import { useSyncWatcher } from '@/features/tasks/queries';

interface NavItem {
  to: string;
  labelKey: string;
  isActive: (pathname: string) => boolean;
  /** Hidden unless the signed-in user has this permission (admins always see it). */
  permission?: Permission;
  /** Rendered beside the label, for items that can demand attention. */
  badge?: () => ReactNode;
}

interface SettingsNavItem extends NavItem {
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    labelKey: 'nav.requests',
    isActive: (pathname) => pathname === '/' || pathname.startsWith('/request'),
  },
  {
    to: '/add',
    labelKey: 'nav.add',
    isActive: (pathname) => pathname.startsWith('/add'),
  },
];

// Settings is configuration; System is operational views. The users section is
// the only one a non-admin may reach (a user holding manage_users); the rest are
// admin-only, which the `adminOnly` flag on each marks.
interface SettingsNavItem extends NavItem {
  adminOnly?: boolean;
}

const SETTINGS_ITEMS: SettingsNavItem[] = [
  { to: '/settings/general', labelKey: 'settings.nav.general', isActive: (p) => p.startsWith('/settings/general'), adminOnly: true },
  { to: '/settings/users', labelKey: 'settings.nav.users', isActive: (p) => p.startsWith('/settings/users'), permission: 'manage_users' },
  { to: '/settings/services', labelKey: 'settings.nav.services', isActive: (p) => p.startsWith('/settings/services'), adminOnly: true },
  { to: '/settings/metadata', labelKey: 'settings.nav.metadata', isActive: (p) => p.startsWith('/settings/metadata'), adminOnly: true },
  { to: '/settings/network', labelKey: 'settings.nav.network', isActive: (p) => p.startsWith('/settings/network'), adminOnly: true },
  { to: '/settings/tasks', labelKey: 'settings.nav.tasks', isActive: (p) => p.startsWith('/settings/tasks'), adminOnly: true },
  { to: '/settings/logging', labelKey: 'settings.nav.logging', isActive: (p) => p.startsWith('/settings/logging'), adminOnly: true },
];

const SYSTEM_ITEMS: NavItem[] = [
  { to: '/system/tasks', labelKey: 'nav.tasks', isActive: (p) => p.startsWith('/system/tasks'), permission: 'tasks' },
  { to: '/system/indexers', labelKey: 'nav.indexers', isActive: (p) => p.startsWith('/system/indexers'), permission: 'indexers', badge: () => <IndexerAlertBadge /> },
  { to: '/system/logs', labelKey: 'nav.logs', isActive: (p) => p.startsWith('/system/logs'), permission: 'logs' },
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

function useVisibleNavItems(): NavItem[] {
  const { hasPermission } = useAuth();
  return NAV_ITEMS.filter((item) => !item.permission || hasPermission(item.permission));
}

function useVisibleSystemItems(): NavItem[] {
  const { hasPermission } = useAuth();
  return SYSTEM_ITEMS.filter((item) => !item.permission || hasPermission(item.permission));
}

function useVisibleSettingsItems(): SettingsNavItem[] {
  const { isAdmin, hasPermission } = useAuth();
  return SETTINGS_ITEMS.filter(
    (item) => (item.adminOnly ? isAdmin : true) && (!item.permission || hasPermission(item.permission)),
  );
}

interface NavGroupDef {
  labelKey: string;
  items: NavItem[];
  isActive: (pathname: string) => boolean;
  badge?: () => ReactNode;
}

function useNavGroups(): NavGroupDef[] {
  const settingsItems = useVisibleSettingsItems();
  const systemItems = useVisibleSystemItems();
  const groups: NavGroupDef[] = [];
  if (settingsItems.length > 0) {
    groups.push({
      labelKey: 'nav.settings',
      items: settingsItems,
      isActive: (p) => p.startsWith('/settings'),
    });
  }
  if (systemItems.length > 0) {
    groups.push({
      labelKey: 'nav.system',
      items: systemItems,
      isActive: (p) => p.startsWith('/system'),
    });
  }
  return groups;
}

function UserMenu() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <Menu position="bottom-end" withArrow>
      <Menu.Target>
        <UnstyledButton>
          <Group gap={6} wrap="nowrap">
            <Avatar size="sm" radius="xl" color="blue">
              {user.username.slice(0, 1).toUpperCase()}
            </Avatar>
            <Text size="sm" fw={600} visibleFrom="sm">
              {user.display_name || user.username}
            </Text>
          </Group>
        </UnstyledButton>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Label>{user.username}</Menu.Label>
        <Menu.Item onClick={handleLogout}>{t('auth.logout')}</Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

function Navigation({ onOpenMenu, menuOpened }: { onOpenMenu: () => void; menuOpened: boolean }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const visibleItems = useVisibleNavItems();
  const groups = useNavGroups();

  return (
    <Container size="lg" h="100%" className="safe-area-inline">
      <Group h="100%" justify="space-between" wrap="nowrap" gap="sm">
        <Logo />

        <Group component="nav" gap="lg" wrap="nowrap" visibleFrom="sm">
          {visibleItems.map((item) => {
            const active = item.isActive(pathname);
            return (
              <Group key={item.to} gap={6} wrap="nowrap">
                <Text
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
                {item.badge?.()}
              </Group>
            );
          })}
          {groups.map((group) => {
            const active = group.isActive(pathname);
            return (
              <Menu key={group.labelKey} position="bottom-start" withArrow withinPortal>
                <Menu.Target>
                  <UnstyledButton aria-label={t(group.labelKey)}>
                    <Group gap={4} wrap="nowrap">
                      <Text size="sm" fw={600} c={active ? 'blue.4' : 'dimmed'}>
                        {t(group.labelKey)}
                      </Text>
                      {group.badge?.()}
                    </Group>
                  </UnstyledButton>
                </Menu.Target>
                <Menu.Dropdown>
                  {group.items.map((item) => (
                    <Menu.Item
                      key={item.to}
                      component={Link}
                      to={item.to}
                      rightSection={item.badge?.()}
                      style={{ textDecoration: 'none' }}
                    >
                      {t(item.labelKey)}
                    </Menu.Item>
                  ))}
                </Menu.Dropdown>
              </Menu>
            );
          })}
          <LanguageSwitcher />
          <UserMenu />
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
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const visibleItems = useVisibleNavItems();
  const groups = useNavGroups();

  const handleLogout = async () => {
    onClose();
    await logout();
    navigate('/login', { replace: true });
  };

  /*
   * The panel is full height, so its title would otherwise start under the iOS
   * status bar, and the header's own inset cannot reach a portal.
   */
  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="80%"
      title={<Logo />}
      classNames={{ content: 'safe-area-top' }}
      hiddenFrom="sm"
      zIndex={300}
    >
      <Stack gap="xs" component="nav">
        {visibleItems.map((item) => {
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
              <Group gap={8} wrap="nowrap">
                <Text fw={600} c={active ? 'blue.4' : undefined}>
                  {t(item.labelKey)}
                </Text>
                {item.badge?.()}
              </Group>
            </UnstyledButton>
          );
        })}

        {groups.map((group) => (
          <div key={group.labelKey}>
            <Divider my="sm" />
            <Text size="xs" c="dimmed" tt="uppercase" px="md" pb={4}>
              {t(group.labelKey)}
            </Text>
            {group.items.map((item) => {
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
                  <Group gap={8} wrap="nowrap">
                    <Text fw={600} c={active ? 'blue.4' : undefined}>
                      {t(item.labelKey)}
                    </Text>
                    {item.badge?.()}
                  </Group>
                </UnstyledButton>
              );
            })}
          </div>
        ))}

        <Divider my="sm" />

        <Stack gap={6} px="md">
          <Text size="xs" c="dimmed" tt="uppercase">
            {t('nav.languageLabel')}
          </Text>
          <LanguageSwitcher size="sm" w="100%" />
        </Stack>

        {user ? (
          <>
            <Divider my="sm" />
            <UnstyledButton px="md" py="sm" onClick={handleLogout}>
              <Text fw={600}>{t('auth.logout')}</Text>
            </UnstyledButton>
          </>
        ) : null}
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

  /*
   * A phone has no width to spare: the shell padding and the container padding
   * used to stack into a ~26px gutter on each side, so the cards inside them
   * lost a seventh of the screen before any content was drawn. The shell keeps
   * its padding — it is also what offsets the main area below the fixed header —
   * and the container drops its own inline padding instead.
   */
  return (
    /*
     * The header grows by the top inset rather than being pushed down by it:
     * the shell derives the main area's offset from this height, so both have to
     * come from one value. Mantine passes a `calc()` string through untouched,
     * and the inset is 0 wherever the viewport does not reach under a notch.
     */
    <AppShell
      header={{
        height: {
          base: 'calc(3.5rem + env(safe-area-inset-top))',
          sm: 'calc(4rem + env(safe-area-inset-top))',
        },
      }}
      padding={{ base: 'xs', sm: 'md' }}
    >
      <AppShell.Header
        className="safe-area-top"
        style={{
          backgroundColor: 'rgba(15, 23, 42, 0.92)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <Navigation menuOpened={menuOpened} onOpenMenu={toggleMenu} />
      </AppShell.Header>

      <MobileMenu opened={menuOpened} onClose={closeMenu} />

      <AppShell.Main>
        <Container
          size="lg"
          px={{ base: 0, sm: 'md' }}
          py={{ base: 'xs', sm: 'xl' }}
          className="safe-area-bottom"
        >
          <Outlet />
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}

export default AppLayout;
