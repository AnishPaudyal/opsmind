import { describe, expect, it } from "vitest";

import { apiErrorFromResponse, networkApiError } from "./errors";

describe("API error normalization", () => {
  it.each([
    [404, "not_found"],
    [409, "conflict"],
    [422, "validation"],
    [500, "unexpected"],
    [502, "unavailable"],
    [503, "unavailable"],
    [504, "unavailable"],
  ] as const)("maps status %s to %s", (status, kind) => {
    const error = apiErrorFromResponse(
      new Response(null, {
        status,
        headers: {
          "X-Request-ID": "request-id",
          "X-OpsMind-Revision": "revision",
        },
      }),
      { detail: " Bounded backend detail. " },
    );
    expect(error).toMatchObject({
      kind,
      status,
      requestId: "request-id",
      revision: "revision",
    });
    expect(error.message).toContain(
      kind === "unavailable" || kind === "unexpected"
        ? "OpsMind"
        : "Bounded backend detail.",
    );
  });

  it("uses safe defaults for absent or structured details and bounds headers", () => {
    const error = apiErrorFromResponse(
      new Response(null, {
        status: 422,
        headers: { "X-Request-ID": "x".repeat(129) },
      }),
      { detail: [{ msg: "private field detail" }] },
    );
    expect(error.message).toBe("The request did not match the API contract.");
    expect(error.requestId).toBeUndefined();
    expect(networkApiError()).toMatchObject({ kind: "unavailable" });
  });
});
