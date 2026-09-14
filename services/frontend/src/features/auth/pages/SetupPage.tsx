import { Alert, Button, Paper, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core';
import { type FormEvent, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/AuthProvider';

export function SetupPage() {
  const { t } = useTranslation();
  const { completeSetup, status } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // This route sits outside RequireAuth's guard: if setup has already been
  // completed (elsewhere, or by another tab), a stale tab here would otherwise
  // never notice and would keep offering to create a second admin account.
  useEffect(() => {
    if (status === 'authenticated') {
      navigate('/', { replace: true });
    } else if (status === 'anonymous') {
      navigate('/login', { replace: true });
    }
  }, [status, navigate]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (!username.trim()) {
      setError(t('auth.setup.usernameRequired'));
      return;
    }
    if (password.length < 8) {
      setError(t('auth.setup.passwordTooShort'));
      return;
    }

    setSubmitting(true);
    try {
      await completeSetup(username.trim(), password, displayName.trim());
      navigate('/', { replace: true });
    } catch {
      setError(t('auth.setup.error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack align="center" justify="center" mih="80vh">
      <Paper withBorder p="xl" radius="md" w={400}>
        <Stack gap="md">
          <Title order={2} ta="center">
            {t('auth.setup.title')}
          </Title>
          <Text size="sm" c="dimmed" ta="center">
            {t('auth.setup.subtitle')}
          </Text>
          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              {error ? (
                <Alert color="red" variant="light">
                  {error}
                </Alert>
              ) : null}
              <TextInput
                label={t('auth.setup.username')}
                autoComplete="username"
                autoFocus
                required
                value={username}
                onChange={(event) => setUsername(event.currentTarget.value)}
              />
              <TextInput
                label={t('auth.setup.displayName')}
                value={displayName}
                onChange={(event) => setDisplayName(event.currentTarget.value)}
              />
              <PasswordInput
                label={t('auth.setup.password')}
                autoComplete="new-password"
                required
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
              />
              <Button type="submit" loading={submitting} fullWidth>
                {t('auth.setup.submit')}
              </Button>
            </Stack>
          </form>
        </Stack>
      </Paper>
    </Stack>
  );
}
