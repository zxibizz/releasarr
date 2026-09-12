import { Alert, Code, Stack, Table, Text } from '@mantine/core';
import { useTranslation } from 'react-i18next';

interface JobOutputProps {
  result?: Record<string, unknown> | null;
  error?: string | null;
}

const renderValue = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

/**
 * What a run reported: the summary counters it produced and, when it failed,
 * why. This is everything the scheduler records about a single run.
 */
export function JobOutput({ result, error }: JobOutputProps) {
  const { t } = useTranslation();
  const entries = Object.entries(result ?? {});

  if (entries.length === 0 && !error) {
    return (
      <Text size="sm" c="dimmed">
        {t('tasks.output.empty')}
      </Text>
    );
  }

  return (
    <Stack gap="sm">
      {error && (
        <Alert color="red" variant="light" radius="md" title={t('tasks.output.errorTitle')}>
          <Code block>{error}</Code>
        </Alert>
      )}

      {entries.length > 0 && (
        <Table withTableBorder withColumnBorders verticalSpacing={4} fz="sm">
          <Table.Tbody>
            {entries.map(([key, value]) => (
              <Table.Tr key={key}>
                <Table.Th w="40%">
                  <Text size="sm" c="dimmed" ff="monospace">
                    {key}
                  </Text>
                </Table.Th>
                <Table.Td>
                  <Text size="sm" ff="monospace">
                    {renderValue(value)}
                  </Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Stack>
  );
}
