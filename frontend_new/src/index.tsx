import { ChakraProvider } from "@chakra-ui/react";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { RequestsProvider } from "./hooks/useRequests";
import { ReleasesProvider } from "./hooks/useReleases";
import reportWebVitals from "./reportWebVitals";
import theme from "./theme";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations
      .filter((registration) =>
        registration.active?.scriptURL?.includes("mockServiceWorker.js")
      )
      .forEach((registration) => registration.unregister());
  });
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <ChakraProvider theme={theme}>
      <RequestsProvider>
        <ReleasesProvider>
          <App />
        </ReleasesProvider>
      </RequestsProvider>
    </ChakraProvider>
  </React.StrictMode>
);
reportWebVitals();
