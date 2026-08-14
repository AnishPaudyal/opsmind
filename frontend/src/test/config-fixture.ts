import {
  OPSMIND_ZITADEL_CLIENT_ID,
  OPSMIND_ZITADEL_ISSUER,
  OPSMIND_ZITADEL_PROJECT_ID,
  type PublicConfig,
} from "../config";

export const publicConfig: PublicConfig = Object.freeze({
  apiBaseUrl: "http://127.0.0.1:8000",
  environment: "test",
  zitadelIssuer: OPSMIND_ZITADEL_ISSUER,
  zitadelProjectId: OPSMIND_ZITADEL_PROJECT_ID,
  zitadelClientId: OPSMIND_ZITADEL_CLIENT_ID,
  browserOrigin: "http://localhost:5173",
  redirectUri: "http://localhost:5173/auth/callback",
  postLogoutRedirectUri: "http://localhost:5173/",
});
