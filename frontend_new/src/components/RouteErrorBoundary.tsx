import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Code,
  HStack,
  Stack,
  Tag,
  Text,
} from '@chakra-ui/react';
import {
  isRouteErrorResponse,
  useNavigate,
  useRouteError,
} from 'react-router-dom';

import { formatErrorDebugInfo, getApiErrorInfo } from '@/utils/errors';

import { NotFound } from './NotFound';

type RouterErrorResponse = {
  data?: unknown;
  status: number;
  statusText: string;
};

const getRouteErrorDescription = (error: RouterErrorResponse): string => {
  if (typeof error.data === 'string' && error.data.trim().length > 0) {
    return error.data;
  }

  if (error.data && typeof (error.data as { message?: unknown }).message === 'string') {
    return String((error.data as { message: string }).message);
  }

  return error.statusText || 'An unexpected error occurred while rendering this page.';
};

export const RouteErrorBoundary = () => {
  const error = useRouteError();
  const navigate = useNavigate();

  if (isRouteErrorResponse(error)) {
    if (error.status === 404) {
      return <NotFound />;
    }

    const description = getRouteErrorDescription(error);

    return (
      <Stack spacing={6} py={{ base: 8, md: 12 }}>
        <Alert
          status="error"
          variant="left-accent"
          borderRadius="xl"
          borderLeftWidth={4}
          alignItems="flex-start"
          p={{ base: 5, md: 6 }}
        >
          <AlertIcon boxSize={6} mt={1} />
          <Stack spacing={3} flex="1">
            <HStack spacing={3} align="center">
              <AlertTitle fontSize="lg" fontWeight="semibold">
                {error.status} {error.statusText || 'Request failed'}
              </AlertTitle>
              <Tag colorScheme="red" variant="subtle">
                Router Error
              </Tag>
            </HStack>
            <AlertDescription>{description}</AlertDescription>
            <HStack spacing={3} pt={2} flexWrap="wrap">
              <Button colorScheme="blue" onClick={() => navigate(0)}>
                Try Again
              </Button>
              <Button variant="outline" onClick={() => navigate('/') }>
                Back to Requests
              </Button>
            </HStack>
          </Stack>
        </Alert>
      </Stack>
    );
  }

  const fallback = {
    title: 'Something went wrong',
    description: 'We hit an unexpected issue while loading this view.',
  };
  const info = getApiErrorInfo(error, fallback);
  const debugDetails = formatErrorDebugInfo(error);

  return (
    <Stack spacing={6} py={{ base: 8, md: 12 }}>
      <Alert
        status="error"
        variant="left-accent"
        borderRadius="xl"
        borderLeftWidth={4}
        alignItems="flex-start"
        p={{ base: 5, md: 6 }}
      >
        <AlertIcon boxSize={6} mt={1} />
        <Stack spacing={3} flex="1">
          <HStack spacing={3} align="center">
            <AlertTitle fontSize="lg" fontWeight="semibold">
              {info.title ?? 'Unexpected Error'}
            </AlertTitle>
            {info.status ? (
              <Tag colorScheme="red" variant="subtle">
                {info.status}
              </Tag>
            ) : (
              <Tag colorScheme="orange" variant="subtle">
                Client Error
              </Tag>
            )}
          </HStack>
          <AlertDescription>{info.description}</AlertDescription>
          <HStack spacing={3} pt={2} flexWrap="wrap">
            <Button colorScheme="blue" onClick={() => navigate(0)}>
              Try Again
            </Button>
            <Button variant="outline" onClick={() => navigate('/') }>
              Back to Requests
            </Button>
          </HStack>
        </Stack>
      </Alert>

      {debugDetails && (
        <Box
          borderWidth="1px"
          borderRadius="lg"
          borderColor="border.muted"
          bg="bg.subtle"
          p={4}
        >
          <Text fontSize="sm" color="text.subtle" mb={2}>
            Error details
          </Text>
          <Code
            display="block"
            whiteSpace="pre"
            overflowX="auto"
            fontSize="xs"
            p={4}
            width="full"
            bg="rgba(15, 23, 42, 0.8)"
            color="slate.100"
          >
            {debugDetails}
          </Code>
        </Box>
      )}
    </Stack>
  );
};

export default RouteErrorBoundary;
