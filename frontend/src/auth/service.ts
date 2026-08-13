import {
  UserManager,
  WebStorageStateStore,
  type User,
  type UserManagerSettings,
} from "oidc-client-ts";

import type { PublicConfig } from "../config";
import { rolesForPresentation, type OpsMindRole } from "./roles";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthSnapshot {
  readonly status: AuthStatus;
  readonly displayName?: string;
  readonly roles: readonly OpsMindRole[];
}

export interface AuthService {
  snapshot(): AuthSnapshot;
  subscribe(listener: (snapshot: AuthSnapshot) => void): () => void;
  restore(): Promise<void>;
  login(returnTo: string): Promise<void>;
  completeLogin(): Promise<string>;
  logout(): Promise<void>;
  getAccessToken(): Promise<string | undefined>;
  clearLocalSession(): Promise<void>;
}

type ManagedUser = Pick<
  User,
  "access_token" | "expired" | "id_token" | "profile" | "state"
>;

export interface OidcManager {
  getUser(): Promise<ManagedUser | null>;
  removeUser(): Promise<void>;
  signinRedirect(args: { state: { returnTo: string } }): Promise<void>;
  signinRedirectCallback(): Promise<ManagedUser>;
  signoutRedirect(args: {
    id_token_hint?: string;
    post_logout_redirect_uri: string;
  }): Promise<void>;
}

export function boundedReturnPath(value: unknown): string {
  if (
    typeof value !== "string" ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.length > 512
  ) {
    return "/";
  }
  return value;
}

export function oidcSettings(
  config: PublicConfig,
  storage: Storage,
): UserManagerSettings {
  return {
    authority: config.zitadelIssuer,
    client_id: config.zitadelClientId,
    redirect_uri: config.redirectUri,
    post_logout_redirect_uri: config.postLogoutRedirectUri,
    response_type: "code",
    disablePKCE: false,
    scope: [
      "openid",
      "profile",
      `urn:zitadel:iam:org:project:id:${config.zitadelProjectId}:aud`,
      "urn:zitadel:iam:org:projects:roles",
    ].join(" "),
    automaticSilentRenew: false,
    monitorSession: false,
    loadUserInfo: false,
    revokeTokensOnSignout: false,
    stateStore: new WebStorageStateStore({ store: storage }),
    userStore: new WebStorageStateStore({ store: storage }),
  };
}

function displayName(user: ManagedUser): string {
  const profile = user.profile as Record<string, unknown>;
  for (const key of ["name", "preferred_username", "sub"]) {
    const candidate = profile[key];
    if (typeof candidate === "string" && candidate.trim() !== "") {
      return candidate.trim().slice(0, 120);
    }
  }
  return "Authenticated operator";
}

export class OidcAuthService implements AuthService {
  readonly #config: PublicConfig;
  readonly #manager: OidcManager;
  readonly #listeners = new Set<(snapshot: AuthSnapshot) => void>();
  #snapshot: AuthSnapshot = { status: "loading", roles: [] };

  constructor(config: PublicConfig, manager?: OidcManager, storage?: Storage) {
    this.#config = config;
    this.#manager =
      manager ??
      new UserManager(oidcSettings(config, storage ?? window.sessionStorage));
  }

  snapshot(): AuthSnapshot {
    return this.#snapshot;
  }

  subscribe(listener: (snapshot: AuthSnapshot) => void): () => void {
    this.#listeners.add(listener);
    listener(this.#snapshot);
    return () => this.#listeners.delete(listener);
  }

  #publish(snapshot: AuthSnapshot): void {
    this.#snapshot = snapshot;
    for (const listener of this.#listeners) {
      listener(snapshot);
    }
  }

  #authenticate(user: ManagedUser): void {
    this.#publish({
      status: "authenticated",
      displayName: displayName(user),
      roles: rolesForPresentation(user.access_token),
    });
  }

  async restore(): Promise<void> {
    const user = await this.#manager.getUser();
    if (user === null || user.expired) {
      if (user?.expired) {
        await this.#manager.removeUser();
      }
      this.#publish({ status: "unauthenticated", roles: [] });
      return;
    }
    this.#authenticate(user);
  }

  async login(returnTo: string): Promise<void> {
    await this.#manager.signinRedirect({
      state: { returnTo: boundedReturnPath(returnTo) },
    });
  }

  async completeLogin(): Promise<string> {
    const user = await this.#manager.signinRedirectCallback();
    if (user.expired) {
      await this.clearLocalSession();
      return "/login";
    }
    this.#authenticate(user);
    const state = user.state as { returnTo?: unknown } | undefined;
    return boundedReturnPath(state?.returnTo);
  }

  async logout(): Promise<void> {
    const user = await this.#manager.getUser();
    await this.#manager.removeUser();
    this.#publish({ status: "unauthenticated", roles: [] });
    const args: { id_token_hint?: string; post_logout_redirect_uri: string } = {
      post_logout_redirect_uri: this.#config.postLogoutRedirectUri,
    };
    if (user?.id_token) {
      args.id_token_hint = user.id_token;
    }
    await this.#manager.signoutRedirect(args);
  }

  async getAccessToken(): Promise<string | undefined> {
    const user = await this.#manager.getUser();
    if (user === null || user.expired || !user.access_token) {
      if (user?.expired) {
        await this.clearLocalSession();
      }
      return undefined;
    }
    return user.access_token;
  }

  async clearLocalSession(): Promise<void> {
    await this.#manager.removeUser();
    this.#publish({ status: "unauthenticated", roles: [] });
  }
}
