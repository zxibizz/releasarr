import { Box, Container, HStack, Link as ChakraLink } from "@chakra-ui/react";
import {
  Route,
  BrowserRouter as Router,
  Routes,
  useLocation,
  Link as RouterLink,
} from "react-router-dom";
import { RequestPage } from "./components/RequestPage";
import { RequestsList } from "./components/RequestsList";

function Navigation() {
  const location = useLocation();

  const navItems = [{ label: "Requests", href: "/" }];

  return (
    <Box
      as="nav"
      position="sticky"
      top={0}
      zIndex="sticky"
      bg="rgba(15, 23, 42, 0.92)"
      backdropFilter="blur(12px)"
      borderBottomWidth="1px"
      borderBottomColor="border.muted"
      py={{ base: 3, md: 4 }}
      px={{ base: 4, md: 8 }}
    >
      <Container maxW="6xl" display="flex" justifyContent="space-between" alignItems="center">
        <ChakraLink
          as={RouterLink}
          to="/"
          fontSize="xl"
          fontWeight="700"
          bgGradient="linear(135deg, #3b82f6, #8b5cf6)"
          bgClip="text"
          _hover={{ textDecoration: "none" }}
        >
          Releasarr
        </ChakraLink>

        <HStack as="ul" spacing={{ base: 4, md: 8 }} listStyleType="none" m={0}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Box as="li" key={item.href} position="relative">
                <ChakraLink
                  as={RouterLink}
                  to={item.href}
                  fontWeight="600"
                  fontSize="sm"
                  color={isActive ? "brand.400" : "text.subtle"}
                  _hover={{ color: "slate.100" }}
                  pb={1}
                >
                  {item.label}
                </ChakraLink>
                {isActive && (
                  <Box
                    position="absolute"
                    left={0}
                    right={0}
                    bottom={-2}
                    height="2px"
                    bgGradient="linear(90deg, #3b82f6, #8b5cf6)"
                    borderRadius="full"
                  />
                )}
              </Box>
            );
          })}
        </HStack>
      </Container>
    </Box>
  );
}

function App() {
  return (
    <Box minH="100vh">
      <Router>
        <Navigation />
        <Container as="main" maxW="6xl" py={{ base: 6, md: 10 }}>
          <Routes>
            <Route path="/" element={<RequestsList />} />
            <Route path="/request/:id" element={<RequestPage />} />
          </Routes>
        </Container>
      </Router>
    </Box>
  );
}

export default App;
