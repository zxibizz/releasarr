import { Button, Code, Group, Stack } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom';

import { EmptyState } from '@/components/EmptyState';

export function RouteErrorBoundary() {
  const error = useRouteError();
  const { t } = useTranslation();

  let title = t('errorBoundary.title', { defaultValue: 'Something went wrong' });
  let description = t('errorBoundary.description', {
    defaultValue: 'An unexpected error occurred while loading this page.',
  });

  if (isRouteErrorResponse(error)) {
    title = `${error.status} ${error.statusText}`;
    description = typeof error.data === 'string' ? error.data : description;
  } else if (error instanceof Error) {
    description = error.message;
  }

  return (
    <EmptyState
      icon="⚠️"
      title={title}
      description={description}
      action={
        <Stack gap="sm" align="center" mt="sm">
          <Group>
            <Button component={Link} to="/" variant="light">
              {t('common.backToRequests', { defaultValue: 'Back to requests' })}
            </Button>
            <Button onClick={() => window.location.reload()}>
              {t('common.tryAgain', { defaultValue: 'Try again' })}
            </Button>
          </Group>
          {import.meta.env.DEV && error instanceof Error && error.stack && (
            <Code block maw={640} style={{ whiteSpace: 'pre-wrap' }}>
              {error.stack}
            </Code>
          )}
        </Stack>
      }
    />
  );
}

export function NotFound() {
  const { t } = useTranslation();

  return (
    <EmptyState
      icon="🧭"
      title={t('notFound.title', { defaultValue: 'Page not found' })}
      description={t('notFound.description', {
        defaultValue: 'The page you are looking for does not exist.',
      })}
      action={
        <Button component={Link} to="/" mt="sm">
          {t('common.backToRequests', { defaultValue: 'Back to requests' })}
        </Button>
      }
    />
  );
}

export default RouteErrorBoundary;
