export const OPSMIND_ROLES = [
  "opsmind.business.read",
  "opsmind.business.write",
  "opsmind.recommendation.decide",
] as const;

export type OpsMindRole = (typeof OPSMIND_ROLES)[number];

const roleSet = new Set<string>(OPSMIND_ROLES);
const projectRolesClaim = "urn:zitadel:iam:org:project:roles";

function decodePayload(accessToken: string): unknown {
  const segment = accessToken.split(".")[1];
  if (segment === undefined || segment.length === 0) {
    return undefined;
  }
  try {
    const normalized = segment.replaceAll("-", "+").replaceAll("_", "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    return JSON.parse(atob(padded)) as unknown;
  } catch {
    return undefined;
  }
}

export function rolesForPresentation(
  accessToken: string | undefined,
): readonly OpsMindRole[] {
  if (accessToken === undefined) {
    return [];
  }
  const payload = decodePayload(accessToken);
  if (typeof payload !== "object" || payload === null) {
    return [];
  }
  const claim = (payload as Record<string, unknown>)[projectRolesClaim];
  if (typeof claim !== "object" || claim === null || Array.isArray(claim)) {
    return [];
  }
  return Object.keys(claim)
    .filter((role): role is OpsMindRole => roleSet.has(role))
    .sort();
}

export function hasPresentationRole(
  roles: readonly OpsMindRole[],
  role: OpsMindRole,
): boolean {
  return roles.includes(role);
}
