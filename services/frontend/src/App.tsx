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
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/useAuth';
import { useSyncWatcher } from '@/features/tasks/queries';
import {
  accessibleSystemItems,
  type NavItem,
  PRIMARY_ITEMS,
  SETTINGS_ITEMS,
} from '@/navigation';

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
  return PRIMARY_ITEMS.filter((item) => !item.permission || hasPermission(item.permission));
}

/** The Settings top-nav link: a direct jump to the first section, admin-only. */
function useSettingsNavItem(): NavItem | null {
  const { isAdmin } = useAuth();
  if (!isAdmin) return null;
  const first = SETTINGS_ITEMS[0];
  return { ...first, labelKey: 'nav.settings', isActive: (p) => p.startsWith('/settings') };
}

/** The System top-nav link: a direct jump to the first page this caller can reach. */
function useSystemNavItem(): NavItem | null {
  const { hasPermission } = useAuth();
  const first = accessibleSystemItems(hasPermission)[0];
  if (!first) return null;
  return { ...first, labelKey: 'nav.system', isActive: (p) => p.startsWith('/system') };
}

function useCombinedNavItems(): NavItem[] {
  const base = useVisibleNavItems();
  const settingsItem = useSettingsNavItem();
  const systemItem = useSystemNavItem();
  return [...base, ...(settingsItem ? [settingsItem] : []), ...(systemItem ? [systemItem] : [])];
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
  const visibleItems = useCombinedNavItems();

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

function MobileNavLink({
  item,
  onClose,
  indented = false,
}: {
  item: NavItem;
  onClose: () => void;
  indented?: boolean;
}) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const active = item.isActive(pathname);

  return (
    <UnstyledButton
      component={Link}
      to={item.to}
      onClick={onClose}
      aria-current={active ? 'page' : undefined}
      pl={indented ? 'xl' : 'md'}
      pr="md"
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
}

function MobileNavSection({
  labelKey,
  items,
  onClose,
}: {
  labelKey: string;
  items: NavItem[];
  onClose: () => void;
}) {
  const { t } = useTranslation();

  return (
    <>
      <Divider mt="sm" />
      <Text px="md" size="xs" fw={700} c="dimmed" tt="uppercase">
        {t(labelKey)}
      </Text>
      {items.map((item) => (
        <MobileNavLink key={item.to} item={item} onClose={onClose} indented />
      ))}
    </>
  );
}

function MobileMenu({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const { user, logout, isAdmin, hasPermission } = useAuth();
  const navigate = useNavigate();
  const primaryItems = useVisibleNavItems();
  const systemItems = accessibleSystemItems(hasPermission);

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
      {/* Settings and System collapse to one link in the header, but a phone has
          no in-page tab strip to drill down with, so they expand here. */}
      <Stack gap="xs" component="nav">
        {primaryItems.map((item) => (
          <MobileNavLink key={item.to} item={item} onClose={onClose} />
        ))}

        {isAdmin ? (
          <MobileNavSection labelKey="nav.settings" items={SETTINGS_ITEMS} onClose={onClose} />
        ) : null}

        {systemItems.length > 0 ? (
          <MobileNavSection labelKey="nav.system" items={systemItems} onClose={onClose} />
        ) : null}

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
