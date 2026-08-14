import { describe, expect, it } from "vitest";

import {
  loadPublicConfig,
  OPSMIND_ZITADEL_CLIENT_ID,
  OPSMIND_ZITADEL_ISSUER,
  OPSMIND_ZITADEL_PROJECT_ID,
  PublicConfigError,
} from "./config";

const validEnvironment = {
  VITE_OPSMIND_API_BASE_URL: "http://127.0.0.1:8000",
  VITE_OPSMIND_ENVIRONMENT: "local",
  VITE_OPSMIND_ZITADEL_ISSUER: OPSMIND_ZITADEL_ISSUER,
  VITE_OPSMIND_ZITADEL_PROJECT_ID: OPSMIND_ZITADEL_PROJECT_ID,
  VITE_OPSMIND_ZITADEL_CLIENT_ID: OPSMIND_ZITADEL_CLIENT_ID,
};

describe("public configuration", () => {
  it("validates the five public values and derives fixed callback locations", () => {
    const config = loadPublicConfig(validEnvironment, "http://localhost:5173");
    expect(config).toMatchObject({
      apiBaseUrl: "http://127.0.0.1:8000",
      browserOrigin: "http://localhost:5173",
      redirectUri: "http://localhost:5173/auth/callback",
      postLogoutRedirectUri: "http://localhost:5173/",
    });
    expect(Object.isFrozen(config)).toBe(true);
  });

  it.each([
    [{ ...validEnvironment, VITE_OPSMIND_API_BASE_URL: undefined }],
    [
      {
        ...validEnvironment,
        VITE_OPSMIND_API_BASE_URL: "https://user:pass@example.test",
      },
    ],
    [
      {
        ...validEnvironment,
        VITE_OPSMIND_API_BASE_URL: "https://api.example.test/path",
      },
    ],
    [{ ...validEnvironment, VITE_OPSMIND_API_BASE_URL: "http://api.example.test" }],
    [{ ...validEnvironment, VITE_OPSMIND_ZITADEL_CLIENT_ID: "wrong-client" }],
    [{ ...validEnvironment, VITE_OPSMIND_ZITADEL_PROJECT_ID: "wrong-project" }],
    [
      {
        ...validEnvironment,
        VITE_OPSMIND_ZITADEL_ISSUER: "https://issuer.example.test",
      },
    ],
  ])("rejects missing, malformed, or unexpected identifiers", (candidate) => {
    expect(() => loadPublicConfig(candidate, "http://localhost:5173")).toThrow(
      PublicConfigError,
    );
  });

  it("rejects every additional VITE value, especially secret-style names", () => {
    expect(() =>
      loadPublicConfig(
        { ...validEnvironment, VITE_OPSMIND_CLIENT_SECRET: "not-a-real-secret" },
        "http://localhost:5173",
      ),
    ).toThrow(PublicConfigError);
    expect(() =>
      loadPublicConfig(
        { ...validEnvironment, VITE_UNREVIEWED_PUBLIC_VALUE: "value" },
        "http://localhost:5173",
      ),
    ).toThrow(PublicConfigError);
  });

  it("requires an HTTPS browser origin except for explicit loopback development", () => {
    expect(() =>
      loadPublicConfig(validEnvironment, "http://portfolio.example.test"),
    ).toThrow(PublicConfigError);
    expect(
      loadPublicConfig(
        { ...validEnvironment, VITE_OPSMIND_API_BASE_URL: "https://api.example.test" },
        "https://opsmind.pages.dev",
      ).browserOrigin,
    ).toBe("https://opsmind.pages.dev");
  });
});
