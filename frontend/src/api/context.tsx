import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useAuth } from "../auth/context";
import type { PublicConfig } from "../config";
import { createOpsMindApi, type OpsMindApi } from "./client";

const ApiContext = createContext<OpsMindApi | undefined>(undefined);

export function ApiProvider({
  children,
  config,
}: {
  readonly children: ReactNode;
  readonly config: PublicConfig;
}) {
  const { getAccessToken, handleUnauthorized } = useAuth();
  const api = useMemo(
    () =>
      createOpsMindApi({
        baseUrl: config.apiBaseUrl,
        getAccessToken,
        onUnauthorized: handleUnauthorized,
      }),
    [config.apiBaseUrl, getAccessToken, handleUnauthorized],
  );
  return <ApiContext.Provider value={api}>{children}</ApiContext.Provider>;
}

export function useApi(): OpsMindApi {
  const api = useContext(ApiContext);
  if (api === undefined) {
    throw new Error("useApi must be used within ApiProvider");
  }
  return api;
}
