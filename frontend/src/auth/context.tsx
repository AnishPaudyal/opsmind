import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { PublicConfig } from "../config";
import { OidcAuthService, type AuthService, type AuthSnapshot } from "./service";

interface AuthContextValue extends AuthSnapshot {
  readonly login: (returnTo: string) => Promise<void>;
  readonly completeLogin: () => Promise<string>;
  readonly logout: () => Promise<void>;
  readonly getAccessToken: () => Promise<string | undefined>;
  readonly handleUnauthorized: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export interface AuthProviderProps {
  readonly children: ReactNode;
  readonly config: PublicConfig;
  readonly service?: AuthService;
}

export function AuthProvider({ children, config, service }: AuthProviderProps) {
  const authService = useMemo(
    () => service ?? new OidcAuthService(config),
    [config, service],
  );
  const [snapshot, setSnapshot] = useState<AuthSnapshot>(authService.snapshot());

  useEffect(() => {
    const unsubscribe = authService.subscribe(setSnapshot);
    void authService.restore().catch(() => authService.clearLocalSession());
    return unsubscribe;
  }, [authService]);

  const login = useCallback(
    (returnTo: string) => authService.login(returnTo),
    [authService],
  );
  const completeLogin = useCallback(() => authService.completeLogin(), [authService]);
  const logout = useCallback(() => authService.logout(), [authService]);
  const getAccessToken = useCallback(() => authService.getAccessToken(), [authService]);
  const handleUnauthorized = useCallback(
    () => authService.clearLocalSession(),
    [authService],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      ...snapshot,
      login,
      completeLogin,
      logout,
      getAccessToken,
      handleUnauthorized,
    }),
    [snapshot, login, completeLogin, logout, getAccessToken, handleUnauthorized],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
