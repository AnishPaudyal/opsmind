import { describe, expect, it } from "vitest";

import { hasPresentationRole, rolesForPresentation } from "./roles";

function unsignedToken(payload: unknown): string {
  const encoded = btoa(JSON.stringify(payload))
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
  return `header.${encoded}.signature`;
}

describe("presentation-only role parsing", () => {
  it("returns only exact known roles in deterministic order", () => {
    const roles = rolesForPresentation(
      unsignedToken({
        "urn:zitadel:iam:org:project:roles": {
          "opsmind.recommendation.decide": { org: "OpsMind" },
          "unknown.admin": { org: "OpsMind" },
          "opsmind.business.read": { org: "OpsMind" },
        },
      }),
    );
    expect(roles).toEqual(["opsmind.business.read", "opsmind.recommendation.decide"]);
    expect(hasPresentationRole(roles, "opsmind.business.read")).toBe(true);
    expect(hasPresentationRole(roles, "opsmind.business.write")).toBe(false);
  });

  it.each([undefined, "invalid", "header.invalid.signature", unsignedToken({})])(
    "grants no presentation role for malformed or absent claims",
    (token) => {
      expect(rolesForPresentation(token)).toEqual([]);
    },
  );
});
