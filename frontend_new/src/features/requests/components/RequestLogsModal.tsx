import {
  Alert,
  AlertDescription,
  AlertIcon,
  Badge,
  Button,
  Center,
  Flex,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  Spinner,
  Stack,
  StackDivider,
  Text,
} from '@chakra-ui/react';
import type { Dispatch, SetStateAction } from 'react';

import { logLevelStyles } from '@/theme/statusStyles';
import type { RequestLogEntry } from '@/types';

interface RequestLogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: RequestLogEntry[];
  requestTitle: string;
  isLoading: boolean;
  error: string | null;
  expandedStacks: Record<string, boolean>;
  setExpandedStacks: Dispatch<SetStateAction<Record<string, boolean>>>;
}

export function RequestLogsModal({
  isOpen,
  onClose,
  logs,
  requestTitle,
  isLoading,
  error,
  expandedStacks,
  setExpandedStacks,
}: RequestLogsModalProps) {
  return (
  <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
    <ModalOverlay />
    <ModalContent maxW="4xl" w="full">
      <ModalHeader>Logs for {requestTitle}</ModalHeader>
      <ModalCloseButton />
      <ModalBody maxH="60vh" overflowY="auto">
        {isLoading ? (
          <Center py={8}>
            <Stack spacing={3} align="center">
              <Spinner color="brand.400" />
              <Text color="text.subtle" fontSize="sm">
                Loading logs...
              </Text>
            </Stack>
          </Center>
        ) : error ? (
          <Alert status="error" variant="left-accent" borderRadius="md">
            <AlertIcon />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : logs.length === 0 ? (
          <Text color="text.subtle">No logs available for this request.</Text>
        ) : (
          <Stack spacing={4} divider={<StackDivider borderColor="border.muted" />}>
            {logs.map((log) => {
              const isExpanded = expandedStacks[log.id];
              return (
                <Stack key={log.id} spacing={3} fontSize="sm">
                  <Flex justify="space-between" align="center" gap={4} wrap="wrap">
                    <Text color="text.subtle">{log.timestamp}</Text>
                    <Flex align="center" gap={2} wrap="wrap">
                      {log.source && (
                        <Badge colorScheme="gray" variant="subtle">
                          {log.source}
                        </Badge>
                      )}
                      <Badge
                        bg={logLevelStyles[log.level].bg}
                        color={logLevelStyles[log.level].color}
                        borderColor={logLevelStyles[log.level].borderColor}
                        borderWidth="1px"
                      >
                        {log.level.toUpperCase()}
                      </Badge>
                    </Flex>
                  </Flex>
                  <Text fontWeight="600" fontSize="md">
                    {log.message}
                  </Text>
                  {log.metadata && (
                    <Stack spacing={2}>
                      <Text fontWeight="600" fontSize="xs" color="text.subtle">
                        Context
                      </Text>
                      <SimpleGrid columns={{ base: 1, sm: 2 }} spacing={2} fontSize="xs">
                        {Object.entries(log.metadata).map(([key, value]) => (
                          <Flex
                            key={key}
                            justify="space-between"
                            gap={3}
                            p={2}
                            borderWidth="1px"
                            borderRadius="md"
                            bg="bg.muted"
                          >
                            <Text fontWeight="600">{key}</Text>
                            <Text color="text.subtle" textAlign="right">
                              {String(value)}
                            </Text>
                          </Flex>
                        ))}
                      </SimpleGrid>
                    </Stack>
                  )}
                  {log.stackTrace && (
                    <Stack spacing={2}>
                      <Button
                        variant="link"
                        size="xs"
                        colorScheme="red"
                        width="fit-content"
                        onClick={() =>
                          setExpandedStacks((prev) => ({
                            ...prev,
                            [log.id]: !prev[log.id],
                          }))
                        }
                      >
                        {isExpanded ? 'Hide stack trace' : 'View stack trace'}
                      </Button>
                      {isExpanded && (
                        <Stack
                          as="pre"
                          fontSize="xs"
                          fontFamily="mono"
                          whiteSpace="pre-wrap"
                          p={3}
                          borderWidth="1px"
                          borderRadius="md"
                          bg="bg.subtle"
                          color="text.subtle"
                          spacing={0}
                        >
                          {log.stackTrace}
                        </Stack>
                      )}
                    </Stack>
                  )}
                </Stack>
              );
            })}
          </Stack>
        )}
      </ModalBody>
      <ModalFooter>
        <Button onClick={onClose}>Close</Button>
      </ModalFooter>
    </ModalContent>
  </Modal>
  );
}
