import { describe, expect, it } from "vitest";

import { ApiError } from "./api/errors";
import { createQueryClient, queryKeys, shouldRetryRead } from "./query";

describe("query policy", () => {
  it("retries only bounded safe-read failures", () => {
    expect(shouldRetryRead(0, new ApiError("wake", { kind: "unavailable" }))).toBe(
      true,
    );
    expect(shouldRetryRead(1, new Error("network"))).toBe(true);
    expect(shouldRetryRead(2, new Error("network"))).toBe(false);
    expect(
      shouldRetryRead(0, new ApiError("forbidden", { kind: "forbidden", status: 403 })),
    ).toBe(false);
  });

  it("disables mutation replay and provides deterministic query keys", () => {
    const client = createQueryClient();
    expect(client.getDefaultOptions().mutations?.retry).toBe(false);
    expect(client.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false);
    expect(queryKeys.inventory("product-1")).toEqual([
      "opsmind",
      "products",
      "product-1",
      "inventory",
    ]);
    expect(queryKeys.demand("product-1")).toEqual([
      "opsmind",
      "products",
      "product-1",
      "demand",
    ]);
    expect(queryKeys.recommendation("review-1")).toEqual([
      "opsmind",
      "recommendations",
      "review-1",
    ]);
  });
});
