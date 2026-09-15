import { MantineProvider } from '@mantine/core';
import { ModalsProvider } from '@mantine/modals';
import { QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import '@/styles/global.css';

import { AppNotifications } from '@/components/AppNotifications';
import { OfflineNotice } from '@/components/OfflineNotice';
import { AuthProvider } from '@/features/auth/AuthProvider';
import '@/lib/i18n';
import { queryClient } from '@/lib/queryClient';
import { UpdatePrompt } from '@/pwa/UpdatePrompt';
import { router } from '@/router';
import { theme } from '@/theme';

const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element #root was not found');
}

createRoot(container).render(
  <StrictMode>
    <MantineProvider theme={theme} forceColorScheme="dark">
      <QueryClientProvider client={queryClient}>
        <ModalsProvider>
          <AppNotifications />
          {/* Outside the router, so an installed app is told about a new build
              and about a dropped connection even while it sits on /login. */}
          <OfflineNotice />
          <UpdatePrompt />
          <AuthProvider>
            <RouterProvider router={router} />
          </AuthProvider>
        </ModalsProvider>
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
