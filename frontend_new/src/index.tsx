import React from 'react';
import ReactDOM from 'react-dom/client';
import { ChakraProvider } from '@chakra-ui/react';
import App from './App';
import reportWebVitals from './reportWebVitals';
import theme from './theme';

const enableMocks = async () => {
  if (process.env.NODE_ENV !== 'development') {
    return;
  }

  const shouldUseMocks = process.env.REACT_APP_USE_MOCKS !== 'false';
  if (!shouldUseMocks) {
    return;
  }

  const { worker } = await import('./mocks/browser');
  await worker.start({
    serviceWorker: {
      url: `${process.env.PUBLIC_URL ?? ''}/mockServiceWorker.js`,
    },
    onUnhandledRequest: 'bypass',
  });
};

enableMocks().finally(() => {
  const rootElement = document.getElementById('root');
  if (!rootElement) {
    throw new Error('Root element not found');
  }

  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <ChakraProvider theme={theme}>
        <App />
      </ChakraProvider>
    </React.StrictMode>
  );
});

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
