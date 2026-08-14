import { z } from "zod";

export const OPSMIND_ZITADEL_ISSUER =
  "https://opsmind-phase-8b-gl9aih.us1.zitadel.cloud";
export const OPSMIND_ZITADEL_PROJECT_ID = "386124341898709869";
export const OPSMIND_ZITADEL_CLIENT_ID = "386124342116795580";

const publicKeys = [
  "VITE_OPSMIND_API_BASE_URL",
  "VITE_OPSMIND_ENVIRONMENT",
  "VITE_OPSMIND_ZITADEL_ISSUER",
  "VITE_OPSMIND_ZITADEL_PROJECT_ID",
  "VITE_OPSMIND_ZITADEL_CLIENT_ID",
] as const;

const publicKeySet = new Set<string>(publicKeys);
const forbiddenPublicKey = /(SECRET|TOKEN|PASSWORD|PRIVATE|DATABASE|CREDENTIAL|KEY)/i;

const publicEnvironmentSchema = z.object({
  VITE_OPSMIND_API_BASE_URL: z.string().trim().min(1),
  VITE_OPSMIND_ENVIRONMENT: z.enum(["local", "test", "staging", "production"]),
  VITE_OPSMIND_ZITADEL_ISSUER: z.literal(OPSMIND_ZITADEL_ISSUER),
  VITE_OPSMIND_ZITADEL_PROJECT_ID: z.literal(OPSMIND_ZITADEL_PROJECT_ID),
  VITE_OPSMIND_ZITADEL_CLIENT_ID: z.literal(OPSMIND_ZITADEL_CLIENT_ID),
});

export interface PublicConfig {
  readonly apiBaseUrl: string;
  readonly environment: "local" | "test" | "staging" | "production";
  readonly zitadelIssuer: typeof OPSMIND_ZITADEL_ISSUER;
  readonly zitadelProjectId: typeof OPSMIND_ZITADEL_PROJECT_ID;
  readonly zitadelClientId: typeof OPSMIND_ZITADEL_CLIENT_ID;
  readonly browserOrigin: string;
  readonly redirectUri: string;
  readonly postLogoutRedirectUri: string;
}

export class PublicConfigError extends Error {
  constructor() {
    super("OpsMind public configuration is missing or invalid.");
    this.name = "PublicConfigError";
  }
}

function exactOrigin(value: string, allowLocalHttp: boolean): string {
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new PublicConfigError();
  }

  const localHostname =
    parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
  const allowedProtocol =
    parsed.protocol === "https:" ||
    (allowLocalHttp && parsed.protocol === "http:" && localHostname);
  if (
    !allowedProtocol ||
    parsed.username !== "" ||
    parsed.password !== "" ||
    parsed.pathname !== "/" ||
    parsed.search !== "" ||
    parsed.hash !== ""
  ) {
    throw new PublicConfigError();
  }
  return parsed.origin;
}

export function loadPublicConfig(
  source: Readonly<Record<string, unknown>> = import.meta.env,
  locationOrigin: string = window.location.origin,
): PublicConfig {
  for (const key of Object.keys(source)) {
    if (
      key.startsWith("VITE_") &&
      (!publicKeySet.has(key) || forbiddenPublicKey.test(key))
    ) {
      throw new PublicConfigError();
    }
  }

  const candidate = Object.fromEntries(publicKeys.map((key) => [key, source[key]]));
  const parsed = publicEnvironmentSchema.safeParse(candidate);
  if (!parsed.success) {
    throw new PublicConfigError();
  }

  const browserOrigin = exactOrigin(locationOrigin, true);
  return Object.freeze({
    apiBaseUrl: exactOrigin(parsed.data.VITE_OPSMIND_API_BASE_URL, true),
    environment: parsed.data.VITE_OPSMIND_ENVIRONMENT,
    zitadelIssuer: parsed.data.VITE_OPSMIND_ZITADEL_ISSUER,
    zitadelProjectId: parsed.data.VITE_OPSMIND_ZITADEL_PROJECT_ID,
    zitadelClientId: parsed.data.VITE_OPSMIND_ZITADEL_CLIENT_ID,
    browserOrigin,
    redirectUri: new URL("/auth/callback", browserOrigin).toString(),
    postLogoutRedirectUri: new URL("/", browserOrigin).toString(),
  });
}
