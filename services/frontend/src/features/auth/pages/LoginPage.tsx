import {
  Alert,
  Button,
  Checkbox,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '@/features/auth/AuthProvider';
import { ApiError } from '@/lib/api/client';

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password, rememberMe);
      const from = (location.state as { from?: Location } | null)?.from;
      navigate(from ? `${from.pathname}${from.search}` : '/', { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 423) {
        setError(t('auth.login.locked'));
      } else if (err instanceof ApiError && err.status === 401) {
        setError(t('auth.login.error'));
      } else {
        setError(t('auth.login.unexpectedError'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack align="center" justify="center" mih="80vh">
      <Paper withBorder p="xl" radius="md" w={360}>
        <Stack gap="md">
          <Title order={2} ta="center">
            {t('auth.login.title')}
          </Title>
          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              {error ? (
                <Alert color="red" variant="light">
                  {error}
                </Alert>
              ) : null}
              <TextInput
                label={t('auth.login.username')}
                autoComplete="username"
                autoFocus
                required
                value={username}
                onChange={(event) => setUsername(event.currentTarget.value)}
              />
              <PasswordInput
                label={t('auth.login.password')}
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.currentTarget.value)}
              />
              <Checkbox
                label={t('auth.login.rememberMe')}
                checked={rememberMe}
                onChange={(event) => setRememberMe(event.currentTarget.checked)}
              />
              <Button type="submit" loading={submitting} fullWidth>
                {t('auth.login.submit')}
              </Button>
            </Stack>
          </form>
        </Stack>
      </Paper>
      <Text size="xs" c="dimmed">
        Releasarr
      </Text>
    </Stack>
  );
}
