import { Badge, Tooltip } from '@mantine/core';
import { useTranslation } from 'react-i18next';

import { isIndexerUnhealthy, useIndexers } from '@/features/indexers/queries';

/**
 * How many indexers need attention, shown beside the navigation link.
 *
 * Prowlarr disables an indexer quietly, so the point of this is to surface that
 * from any page. It renders nothing when the count is zero, and nothing on
 * error either: an unreachable or unconfigured Prowlarr must not leave a
 * permanent warning in the header.
 */
export function IndexerAlertBadge() {
  const { t } = useTranslation();
  const { data, isError } = useIndexers();

  if (isError || !data) {
    return null;
  }

  const count = data.filter(isIndexerUnhealthy).length;
  if (count === 0) {
    return null;
  }

  return (
    <Tooltip label={t('indexers.alert', { count })}>
      <Badge color="red" variant="filled" size="sm" circle>
        {count}
      </Badge>
    </Tooltip>
  );
}
