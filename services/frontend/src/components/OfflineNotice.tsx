import { notifications } from '@mantine/notifications';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { useOnlineStatus } from '@/hooks/useOnlineStatus';

const OFFLINE_NOTIFICATION_ID = 'releasarr-offline';

/**
 * Renders nothing. Keeps one notification in step with the connection so that
 * a page which has quietly stopped updating — every poll in the app is a
 * `refetchInterval` — says why instead of looking stale.
 */
export function OfflineNotice() {
  const isOnline = useOnlineStatus();
  const { t } = useTranslation();

  useEffect(() => {
    if (isOnline) {
      notifications.hide(OFFLINE_NOTIFICATION_ID);
      return;
    }

    notifications.show({
      id: OFFLINE_NOTIFICATION_ID,
      title: t('offline.title', { defaultValue: 'Cannot reach Releasarr' }),
      message: t('offline.notice', {
        defaultValue: 'Your connection dropped. Data may be out of date.',
      }),
      color: 'orange',
      // Every poll in the app is a `refetchInterval`, so dismissing this would
      // leave the visitor without the one explanation for why nothing updates.
      autoClose: false,
      allowClose: false,
    });

    return () => {
      notifications.hide(OFFLINE_NOTIFICATION_ID);
    };
  }, [isOnline, t]);

  return null;
}

export default OfflineNotice;
