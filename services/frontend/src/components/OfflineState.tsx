import { Button } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';

/**
 * The full-page answer to "the browser could not reach the server". Callers
 * decide that it applies; this only renders it, so the same copy and the same
 * single action serve both the auth gate and the route error boundary.
 */
export function OfflineState() {
  const { t } = useTranslation();

  return (
    <EmptyState
      icon="📡"
      title={t('offline.title', { defaultValue: 'Cannot reach Releasarr' })}
      description={t('offline.description', {
        defaultValue: 'The app could not reach the server. Check your connection, then try again.',
      })}
      action={
        <Button onClick={() => window.location.reload()} mt="sm">
          {t('offline.reload', { defaultValue: 'Reload' })}
        </Button>
      }
    />
  );
}

export default OfflineState;
