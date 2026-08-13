import { describe, expect, it, vi } from "vitest";

import { publicConfig } from "../test/config-fixture";
import {
  boundedReturnPath,
  OidcAuthService,
  oidcSettings,
  type OidcManager,
} from "./service";

function manager(overrides: Partial<OidcManager> = {}): OidcManager {
  return {
    getUser: vi.fn().mockResolvedValue(null),
    removeUser: vi.fn().mockResolvedValue(undefined),
    signinRedirect: vi.fn().mockResolvedValue(undefined),
    signinRedirectCallback: vi.fn().mockRejectedValue(new Error("not configured")),
    signoutRedirect: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

const activeUser = {
  access_token:
    "header.eyJ1cm46eml0YWRlbDppYW06b3JnOnByb2plY3Q6cm9sZXMiOnt9fQ.signature",
  expired: false,
  id_token: "synthetic-id-token",
  profile: { name: "Portfolio Operator", sub: "public-subject" },
  state: { returnTo: "/products" },
};

describe("OIDC auth service", () => {
  it("uses code flow, exact scopes, and sessionStorage only", async () => {
    window.localStorage.setItem("sentinel", "untouched");
    const settings = oidcSettings(publicConfig, window.sessionStorage);
    expect(settings).toMatchObject({
      response_type: "code",
      disablePKCE: false,
      automaticSilentRenew: false,
      monitorSession: false,
      loadUserInfo: false,
    });
    expect(settings.scope?.split(" ")).toEqual([
      "openid",
      "profile",
      "urn:zitadel:iam:org:project:id:386124341898709869:aud",
      "urn:zitadel:iam:org:projects:roles",
    ]);
    expect(settings.scope).not.toContain("offline_access");

    await settings.stateStore?.set("transaction", "value");
    expect(window.sessionStorage.length).toBe(1);
    expect(window.localStorage.getItem("sentinel")).toBe("untouched");
  });

  it("restores a valid session without exposing the token in the snapshot", async () => {
    const fakeManager = manager({ getUser: vi.fn().mockResolvedValue(activeUser) });
    const service = new OidcAuthService(publicConfig, fakeManager);
    await service.restore();
    expect(service.snapshot()).toEqual({
      status: "authenticated",
      displayName: "Portfolio Operator",
      roles: [],
    });
    expect(JSON.stringify(service.snapshot())).not.toContain("access_token");
    expect(await service.getAccessToken()).toBe(activeUser.access_token);
  });

  it("clears an expired user and fails closed", async () => {
    const removeUser = vi.fn().mockResolvedValue(undefined);
    const fakeManager = manager({
      getUser: vi.fn().mockResolvedValue({ ...activeUser, expired: true }),
      removeUser,
    });
    const service = new OidcAuthService(publicConfig, fakeManager);
    await service.restore();
    expect(removeUser).toHaveBeenCalledOnce();
    expect(service.snapshot().status).toBe("unauthenticated");
    expect(await service.getAccessToken()).toBeUndefined();
  });

  it("bounds return paths for login and callback", async () => {
    const signinRedirect = vi.fn().mockResolvedValue(undefined);
    const fakeManager = manager({
      signinRedirect,
      signinRedirectCallback: vi.fn().mockResolvedValue(activeUser),
    });
    const service = new OidcAuthService(publicConfig, fakeManager);
    await service.login("//attacker.example/path");
    expect(signinRedirect).toHaveBeenCalledWith({ state: { returnTo: "/" } });
    expect(await service.completeLogin()).toBe("/products");
    expect(boundedReturnPath("/products?active=true")).toBe("/products?active=true");
    expect(boundedReturnPath("https://attacker.example")).toBe("/");
  });

  it("removes local state before starting provider logout", async () => {
    const removeUser = vi.fn().mockResolvedValue(undefined);
    const signoutRedirect = vi.fn().mockResolvedValue(undefined);
    const fakeManager = manager({
      getUser: vi.fn().mockResolvedValue(activeUser),
      removeUser,
      signoutRedirect,
    });
    const service = new OidcAuthService(publicConfig, fakeManager);
    await service.restore();
    await service.logout();
    expect(removeUser).toHaveBeenCalled();
    expect(signoutRedirect).toHaveBeenCalledWith({
      id_token_hint: "synthetic-id-token",
      post_logout_redirect_uri: "http://localhost:5173/",
    });
    expect(service.snapshot().status).toBe("unauthenticated");
  });

  it("handles expired callbacks and logout without an ID token", async () => {
    const removeUser = vi.fn().mockResolvedValue(undefined);
    const signoutRedirect = vi.fn().mockResolvedValue(undefined);
    const fakeManager = manager({
      getUser: vi.fn().mockResolvedValue(null),
      removeUser,
      signinRedirectCallback: vi
        .fn()
        .mockResolvedValue({ ...activeUser, expired: true }),
      signoutRedirect,
    });
    const service = new OidcAuthService(publicConfig, fakeManager);
    expect(await service.completeLogin()).toBe("/login");
    await service.logout();
    expect(signoutRedirect).toHaveBeenCalledWith({
      post_logout_redirect_uri: "http://localhost:5173/",
    });
  });
});
