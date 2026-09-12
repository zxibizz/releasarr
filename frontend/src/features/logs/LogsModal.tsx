import {
  Alert,
  Badge,
  Button,
  Code,
  Collapse,
  Group,
  Loader,
  Modal,
  Paper,
  Stack,
  Text,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { useTranslation } from 'react-i18next';

import { EmptyState } from '@/components/EmptyState';
import { formatLogContext } from '@/features/logs/context';
import { useRequestLogs } from '@/features/logs/queries';
import type { RequestLogEntry } from '@/types';
import { getErrorMessage } from '@/utils/errors';
import { LOG_LEVEL_COLOR } from '@/utils/status';

interface LogsModalProps {
  requestId: string;
  requestTitle: string;
  opened: boolean;
  onClose: () => void;
}

/** The request is already named in the title, so repeating its id adds nothing. */
const HIDDEN_METADATA_KEYS = ['request_id'];

function LogRow({ entry }: { entry: RequestLogEntry }) {
  const { t } = useTranslation();
  const [stackOpened, stack] = useDisclosure(false);

  const context = formatLogContext(entry.metadata, HIDDEN_METADATA_KEYS);

  return (
    <Paper withBorder radius="md" p="md">
      <Stack gap={6}>
        <Group gap="xs" wrap="nowrap">
          <Badge color={LOG_LEVEL_COLOR[entry.level]} variant="light">
            {entry.level}
          </Badge>
          <Text size="sm" c="dimmed">
            {entry.timestamp}
          </Text>
          {entry.source ? (
            <Text size="sm" c="dimmed" truncate>
              {entry.source}
            </Text>
          ) : null}
        </Group>

        <Text style={{ wordBreak: 'break-word' }}>{entry.message}</Text>

        {context ? (
          <Text size="xs" c="dimmed" style={{ wordBreak: 'break-word' }}>
            {t('requestLogsModal.context')}: {context}
          </Text>
        ) : null}

        {entry.stackTrace ? (
          <Stack gap={6}>
            <Button variant="subtle" size="compact-xs" onClick={stack.toggle} w="fit-content">
              {stackOpened
                ? t('requestLogsModal.stackTrace.hide')
                : t('requestLogsModal.stackTrace.show')}
            </Button>
            <Collapse expanded={stackOpened}>
              <Code block>{entry.stackTrace}</Code>
            </Collapse>
          </Stack>
        ) : null}
      </Stack>
    </Paper>
  );
}

export function LogsModal({ requestId, requestTitle, opened, onClose }: LogsModalProps) {
  const { t } = useTranslation();
  const { data, isPending, isFetching, error } = useRequestLogs(requestId, opened);

  const logs = data?.logs ?? [];

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      title={t('requestLogsModal.title', { title: requestTitle })}
    >
      <Stack gap="sm">
        {error ? (
          <Alert color="red" title={t('requestPage.errors.loadLogsTitle')}>
            {getErrorMessage(error, t('requestPage.errors.loadLogsDescription'))}
          </Alert>
        ) : null}

        {isFetching ? (
          <Group gap="xs">
            <Loader size="xs" />
            <Text size="sm" c="dimmed">
              {t('requestLogsModal.refreshing')}
            </Text>
          </Group>
        ) : null}

        {!isPending && !error && logs.length === 0 ? (
          <EmptyState icon="📋" title={t('requestLogsModal.empty')} />
        ) : null}

        {logs.map((entry) => (
          <LogRow key={entry.id} entry={entry} />
        ))}
      </Stack>
    </Modal>
  );
}
