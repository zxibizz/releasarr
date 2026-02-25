import type { Preview } from '@storybook/react';
import { ChakraProvider } from '@chakra-ui/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';

import theme from '../src/theme';

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
    backgrounds: {
      default: 'app-canvas',
      values: [
        { name: 'app-canvas', value: '#0b1220' },
        { name: 'surface', value: 'rgba(30, 41, 59, 0.9)' },
        { name: 'light', value: '#f8fafc' },
      ],
    },
  },
  decorators: [
    (Story) => (
      <ChakraProvider theme={theme}>
        <MemoryRouter>
          <Story />
        </MemoryRouter>
      </ChakraProvider>
    ),
  ],
};

export default preview;
