import { Button, Card, SimpleGrid, Stack, Text } from '@chakra-ui/react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

export interface RequestActionItem {
  title: string;
  description: string;
  icon: ReactNode;
  isLoading?: boolean;
  isDisabled?: boolean;
  loadingText?: string;
  onClick?: () => void;
}

interface RequestActionsProps {
  actions: RequestActionItem[];
}

export function RequestActions({ actions }: RequestActionsProps) {
  const { t } = useTranslation();

  return (
    <Card p={{ base: 5, md: 6 }}>
      <Stack spacing={4}>
        <Text as="h2" fontSize="lg" fontWeight="700">
          {t('requestActions.title')}
        </Text>
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          {actions.map((action) => (
            <Card
              key={action.title}
              p={4}
              bg="bg.subtle"
              borderWidth="1px"
              borderColor="border.muted"
              as={Button}
              variant="ghost"
              colorScheme="gray"
              textAlign="left"
              height="auto"
              flexDirection="column"
              alignItems="flex-start"
              onClick={() => action.onClick?.()}
              isDisabled={action.isDisabled}
              isLoading={action.isLoading}
              loadingText={action.loadingText}
            >
              <Text fontSize="2xl" mb={2}>
                {action.icon}
              </Text>
              <Text fontWeight="600" mb={1}>
                {action.title}
              </Text>
              <Text fontSize="sm" color="text.subtle">
                {action.description}
              </Text>
            </Card>
          ))}
        </SimpleGrid>
      </Stack>
    </Card>
  );
}
