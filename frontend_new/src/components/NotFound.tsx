import { Button, Card, Heading, Stack, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";

export const NotFound = () => {
  return (
    <Card py={12} px={{ base: 6, md: 10 }} textAlign="center" bg="bg.subtle" borderRadius="xl">
      <Stack spacing={6} align="center">
        <Text fontSize="5xl" role="img" aria-label="Astronaut">
          🧭
        </Text>
        <Stack spacing={2} align="center">
          <Heading size="lg">Page not found</Heading>
          <Text color="text.subtle" maxW="sm">
            The page you&apos;re looking for doesn&apos;t exist or may have moved. Let&apos;s
            get you back to the requests dashboard.
          </Text>
        </Stack>
        <Button as={RouterLink} to="/" colorScheme="blue">
          ← Back to Requests
        </Button>
      </Stack>
    </Card>
  );
};
