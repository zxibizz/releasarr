import { Anchor, Button, Center, Loader, NumberInput, Stack, Table, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { SettingsSectionForm } from '@/features/settings/components/SettingsSectionForm';
import { useScheduledTasks, useUpdateTaskInterval } from '@/features/tasks/queries';
import type { SyncJobKind } from '@/types';

const MIN_SECONDS = 5;

function IntervalRow({
  kind,
  intervalSeconds,
}: {
  kind: SyncJobKind;
  intervalSeconds: number;
}) {
  const { t } = useTranslation();
  const update = useUpdateTaskInterval();
  const [value, setValue] = useState<number | string>(intervalSeconds);

  const dirty = typeof value === 'number' && value !== intervalSeconds && value >= MIN_SECONDS;

  return (
    <Table.Tr>
      <Table.Td>
        <Text size="sm" fw={500}>
          {t(`settings.tasks.kinds.${kind}`, { defaultValue: kind })}
        </Text>
      </Table.Td>
      <Table.Td>
        <NumberInput
          aria-label={t(`settings.tasks.kinds.${kind}`, { defaultValue: kind })}
          min={MIN_SECONDS}
          value={value}
          onChange={setValue}
          w={140}
          size="sm"
        />
      </Table.Td>
      <Table.Td>
        <Button
          size="xs"
          disabled={!dirty}
          loading={update.isPending && update.variables?.kind === kind}
          onClick={() => update.mutate({ kind, intervalSeconds: Number(value) })}
        >
          {t('common.save')}
        </Button>
      </Table.Td>
    </Table.Tr>
  );
}

export function TasksSettingsPage() {
  const { t } = useTranslation();
  const { data: tasks, isPending } = useScheduledTasks();

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>{t('settings.tasks.title')}</Title>
        <Text c="dimmed" size="sm" mt={4}>
          {t('settings.tasks.description')}{' '}
          <Anchor component={Link} to="/system/tasks" size="sm">
            {t('settings.tasks.viewSystem')}
          </Anchor>
        </Text>
      </div>

      {isPending ? (
        <Center mih="30vh">
          <Loader />
        </Center>
      ) : (
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>{t('settings.tasks.task')}</Table.Th>
              <Table.Th>{t('settings.tasks.intervalSeconds')}</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(tasks ?? []).map((task) => (
              // Keyed by the saved interval so a saved edit remounts the row and
              // re-seeds the draft, instead of syncing it through an effect.
              <IntervalRow
                key={`${task.kind}:${task.interval_seconds}`}
                kind={task.kind}
                intervalSeconds={task.interval_seconds}
              />
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* The interval table edits `scheduled_tasks`; these come from the settings
          registry, and both are read at the start of every scheduler loop. */}
      <SettingsSectionForm
        section="tasks"
        titleKey="settings.tasks.regrabTitle"
        descriptionKey="settings.tasks.regrabDescription"
        titleOrder={3}
      />
    </Stack>
  );
}
