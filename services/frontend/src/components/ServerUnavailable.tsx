import { Button } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';

/**
 * The full-page answer to "the server answered, but said it is down" — a 5xx
 * while the auth bootstrap was asking. Sibling to OfflineState, which covers
 * the request never reaching the server at all.
 */
export function ServerUnavailable() {
  const { t } = useTranslation();

  return (
    <EmptyState
      icon="🚧"
      title={t('serverUnavailable.title', { defaultValue: 'Releasarr is unavailable' })}
      description={t('serverUnavailable.description', {
        defaultValue: 'The server is not responding. It may be restarting — try again shortly.',
      })}
      action={
        <Button onClick={() => window.location.reload()} mt="sm">
          {t('serverUnavailable.reload', { defaultValue: 'Refresh' })}
        </Button>
      }
    />
  );
}

export default ServerUnavailable;
