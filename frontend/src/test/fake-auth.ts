import type { OpsMindRole } from "../auth/roles";
import type { AuthService, AuthSnapshot } from "../auth/service";

export class FakeAuthService implements AuthService {
  readonly loginCalls: string[] = [];
  logoutCalls = 0;
  unauthorizedCalls = 0;
  callbackReturn = "/";
  callbackError = false;
  token: string | undefined;
  #listeners = new Set<(snapshot: AuthSnapshot) => void>();
  #snapshot: AuthSnapshot;

  constructor(
    status: AuthSnapshot["status"] = "unauthenticated",
    roles: readonly OpsMindRole[] = [],
  ) {
    this.#snapshot = {
      status,
      ...(status === "authenticated" ? { displayName: "Portfolio Operator" } : {}),
      roles,
    };
  }

  snapshot(): AuthSnapshot {
    return this.#snapshot;
  }

  subscribe(listener: (snapshot: AuthSnapshot) => void): () => void {
    this.#listeners.add(listener);
    listener(this.#snapshot);
    return () => this.#listeners.delete(listener);
  }

  emit(snapshot: AuthSnapshot): void {
    this.#snapshot = snapshot;
    for (const listener of this.#listeners) {
      listener(snapshot);
    }
  }

  restore(): Promise<void> {
    this.emit(this.#snapshot);
    return Promise.resolve();
  }

  login(returnTo: string): Promise<void> {
    this.loginCalls.push(returnTo);
    return Promise.resolve();
  }

  completeLogin(): Promise<string> {
    if (this.callbackError) {
      return Promise.reject(new Error("synthetic callback failure"));
    }
    this.emit({
      status: "authenticated",
      displayName: "Portfolio Operator",
      roles: [],
    });
    return Promise.resolve(this.callbackReturn);
  }

  logout(): Promise<void> {
    this.logoutCalls += 1;
    this.emit({ status: "unauthenticated", roles: [] });
    return Promise.resolve();
  }

  getAccessToken(): Promise<string | undefined> {
    return Promise.resolve(this.token);
  }

  clearLocalSession(): Promise<void> {
    this.unauthorizedCalls += 1;
    this.token = undefined;
    this.emit({ status: "unauthenticated", roles: [] });
    return Promise.resolve();
  }
}
