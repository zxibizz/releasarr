import { Button, Stack, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useRegisterSW } from 'virtual:pwa-register/react';

const UPDATE_NOTIFICATION_ID = 'releasarr-update';

/** How often an already-open tab asks whether a newer build has been deployed. */
const UPDATE_CHECK_INTERVAL_MS = 60 * 60 * 1000;

/**
 * Renders nothing. Owns both halves of the update story: a background check so
 * a tab that is never closed still learns about a deploy, and a prompt so the
 * visitor can take the new build on the spot. Ignoring the prompt is safe —
 * the waiting worker takes over on the next cold start either way.
 */
export function UpdatePrompt() {
  const { t } = useTranslation();
  const registrationRef = useRef<ServiceWorkerRegistration | null>(null);

  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW(_swUrl, registration) {
      registrationRef.current = registration ?? null;
    },
  });

  useEffect(() => {
    const check = () => {
      const registration = registrationRef.current;
      if (registration) {
        void registration.update().catch(() => {});
      }
    };

    // A client-side route change is not a navigation as far as the browser is
    // concerned, so without this a tab open since the last deploy would keep
    // running it until it was closed.
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        check();
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    const timer = window.setInterval(check, UPDATE_CHECK_INTERVAL_MS);
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!needRefresh) {
      return;
    }

    notifications.show({
      id: UPDATE_NOTIFICATION_ID,
      title: t('pwa.updateAvailable.title', { defaultValue: 'Update available' }),
      // The store has no slot for an action, so the button lives in the body.
      message: (
        <Stack gap="xs" mt={4}>
          <Text size="sm">
            {t('pwa.updateAvailable.description', {
              defaultValue: 'A newer version of Releasarr is ready.',
            })}
          </Text>
          <Button size="xs" variant="light" onClick={() => void updateServiceWorker(true)}>
            {t('pwa.updateAvailable.action', { defaultValue: 'Reload' })}
          </Button>
        </Stack>
      ),
      color: 'blue',
      autoClose: false,
      withCloseButton: false,
    });
  }, [needRefresh, t, updateServiceWorker]);

  return null;
}

export default UpdatePrompt;
