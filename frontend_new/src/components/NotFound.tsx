import { Button, Card, Heading, Stack, Text } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';

export const NotFound = () => {
  const { t } = useTranslation();

  return (
    <Card py={12} px={{ base: 6, md: 10 }} textAlign="center" bg="bg.subtle" borderRadius="xl">
      <Stack spacing={6} align="center">
        <Text fontSize="5xl" role="img" aria-label="Astronaut">
          🧭
        </Text>
        <Stack spacing={2} align="center">
          <Heading size="lg">{t('notFound.title')}</Heading>
          <Text color="text.subtle" maxW="sm">
            {t('notFound.description')}
          </Text>
        </Stack>
        <Button as={RouterLink} to="/" colorScheme="blue">
          {t('common.backToRequests')}
        </Button>
      </Stack>
    </Card>
  );
};
