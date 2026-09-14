import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { IconCopy } from '@tabler/icons-react';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Panel } from '@/components/Panel';
import {
  useCreateServiceKey,
  useRevokeServiceKey,
  useServiceKeysList,
} from '@/features/users/queries';
import type { ServiceApiKey, User } from '@/types';

/** Admin-only management of hashed service keys, for the bot and similar integrations. */
export function ServiceKeysPanel({ users }: { users: User[] }) {
  const { t } = useTranslation();
  const { serviceKeys, isLoading } = useServiceKeysList();
  const createKey = useCreateServiceKey();
  const revokeKey = useRevokeServiceKey();

  const [formOpened, formModal] = useDisclosure(false);
  const [createdPlaintext, setCreatedPlaintext] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [userId, setUserId] = useState<string | null>(null);
  const [canImpersonate, setCanImpersonate] = useState(false);

  const closeModal = () => {
    formModal.close();
    setCreatedPlaintext(null);
    setName('');
    setUserId(null);
    setCanImpersonate(false);
  };

  const handleCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!userId) {
      return;
    }
    const result = await createKey.mutateAsync({
      name,
      user_id: userId,
      can_impersonate: canImpersonate,
    });
    setCreatedPlaintext(result.plaintext);
  };

  const confirmRevoke = (key: ServiceApiKey) => {
    modals.openConfirmModal({
      title: t('serviceKeys.revoke.title'),
      children: <Text size="sm">{t('serviceKeys.revoke.body', { name: key.name })}</Text>,
      labels: { confirm: t('serviceKeys.revoke.action'), cancel: t('common.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => revokeKey.mutate(key.id),
    });
  };

  return (
    <Stack gap="sm" mt="xl">
      <Group justify="space-between">
        <Text fz="lg" fw={700}>
          {t('serviceKeys.title')}
        </Text>
        <Button variant="light" onClick={formModal.open}>
          {t('serviceKeys.newKey')}
        </Button>
      </Group>
      <Text size="sm" c="dimmed">
        {t('serviceKeys.description')}
      </Text>

      {!isLoading && serviceKeys.length === 0 ? (
        <Text size="sm" c="dimmed">
          {t('serviceKeys.empty')}
        </Text>
      ) : (
        <Panel>
          <Table.ScrollContainer minWidth={560}>
            <Table verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t('serviceKeys.columns.name')}</Table.Th>
                  <Table.Th>{t('serviceKeys.columns.key')}</Table.Th>
                  <Table.Th>{t('serviceKeys.columns.actsAs')}</Table.Th>
                  <Table.Th>{t('serviceKeys.columns.impersonate')}</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {serviceKeys.map((key) => (
                  <Table.Tr key={key.id}>
                    <Table.Td>{key.name}</Table.Td>
                    <Table.Td>
                      <Text ff="monospace" size="sm">
                        {key.prefix}…
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {users.find((user) => user.id === key.user_id)?.username ?? key.user_id}
                    </Table.Td>
                    <Table.Td>
                      <Badge color={key.can_impersonate ? 'grape' : 'gray'} variant="light">
                        {key.can_impersonate ? t('common.yes') : t('common.no')}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        onClick={() => confirmRevoke(key)}
                      >
                        {t('serviceKeys.revoke.action')}
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        </Panel>
      )}

      <Modal opened={formOpened} onClose={closeModal} title={t('serviceKeys.form.title')}>
        {createdPlaintext ? (
          <Stack gap="sm">
            <Alert color="yellow" variant="light">
              {t('serviceKeys.form.onlyShownOnce')}
            </Alert>
            <Group gap="xs" wrap="nowrap" align="flex-start">
              <Text ff="monospace" size="sm" style={{ wordBreak: 'break-all', flex: 1 }}>
                {createdPlaintext}
              </Text>
              <ActionIcon
                variant="light"
                aria-label={t('serviceKeys.form.copy')}
                onClick={() => void navigator.clipboard?.writeText(createdPlaintext)}
              >
                <IconCopy size={16} />
              </ActionIcon>
            </Group>
            <Button onClick={closeModal}>{t('common.close')}</Button>
          </Stack>
        ) : (
          <form onSubmit={handleCreate}>
            <Stack gap="sm">
              <TextInput
                label={t('serviceKeys.form.name')}
                required
                autoFocus
                value={name}
                onChange={(event) => setName(event.currentTarget.value)}
              />
              <Select
                label={t('serviceKeys.form.actsAs')}
                required
                allowDeselect={false}
                data={users.map((user) => ({ value: user.id, label: user.username }))}
                value={userId}
                onChange={setUserId}
              />
              <Checkbox
                label={t('serviceKeys.form.canImpersonate')}
                checked={canImpersonate}
                onChange={(event) => setCanImpersonate(event.currentTarget.checked)}
              />
              <Button type="submit" loading={createKey.isPending}>
                {t('common.save')}
              </Button>
            </Stack>
          </form>
        )}
      </Modal>
    </Stack>
  );
}
