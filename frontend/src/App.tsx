import { QueryClientProvider } from "@tanstack/react-query";
import { useMemo } from "react";
import { BrowserRouter } from "react-router-dom";

import { ApiProvider } from "./api/context";
import { AuthProvider } from "./auth/context";
import type { AuthService } from "./auth/service";
import { ErrorBoundary } from "./components/ErrorBoundary";
import type { PublicConfig } from "./config";
import { createQueryClient } from "./query";
import { AppRoutes } from "./router";

export function App({
  authService,
  config,
}: {
  readonly authService?: AuthService;
  readonly config: PublicConfig;
}) {
  const queryClient = useMemo(() => createQueryClient(), []);
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider
          config={config}
          {...(authService ? { service: authService } : {})}
        >
          <ApiProvider config={config}>
            <BrowserRouter>
              <AppRoutes />
            </BrowserRouter>
          </ApiProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
