import { ChakraProvider } from '@chakra-ui/react';
import { QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import '@/lib/i18n';
import { queryClient } from '@/lib/queryClient';
import reportWebVitals from '@/reportWebVitals';
import { router } from '@/router';
import theme from '@/theme';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations
      .filter((registration) => registration.active?.scriptURL?.includes('mockServiceWorker.js'))
      .forEach((registration) => registration.unregister());
  });
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ChakraProvider theme={theme}>
        <RouterProvider router={router} />
      </ChakraProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);

reportWebVitals();
