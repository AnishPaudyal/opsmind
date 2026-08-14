import { HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { createOpsMindApi } from "./client";
import { ApiError } from "./errors";

const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
});

function api(overrides: Partial<Parameters<typeof createOpsMindApi>[0]> = {}) {
  return createOpsMindApi({
    baseUrl: "https://api.example.test",
    getAccessToken: vi.fn().mockResolvedValue("synthetic-access-token"),
    onUnauthorized: vi.fn().mockResolvedValue(undefined),
    requestIdFactory: () => "00000000-0000-4000-8000-000000000001",
    ...overrides,
  });
}

describe("typed API client", () => {
  it("attaches bearer/request headers centrally and omits credentials", async () => {
    server.use(
      http.get("https://api.example.test/api/v1/products", ({ request }) => {
        expect(request.headers.get("authorization")).toBe(
          "Bearer synthetic-access-token",
        );
        expect(request.headers.get("accept")).toBe("application/json");
        expect(request.headers.get("x-request-id")).toBe(
          "00000000-0000-4000-8000-000000000001",
        );
        expect(request.credentials).toBe("omit");
        return HttpResponse.json([], {
          headers: {
            "X-Request-ID": "server-request-id",
            "X-OpsMind-Revision": "a".repeat(40),
          },
        });
      }),
    );
    const client = api();
    const result = await client.unwrap(client.client.GET("/api/v1/products"));
    expect(result).toEqual({
      data: [],
      requestId: "server-request-id",
      revision: "a".repeat(40),
    });
  });

  it("clears the local session on 401 and keeps 403 distinct", async () => {
    const onUnauthorized = vi.fn().mockResolvedValue(undefined);
    server.use(
      http.get("https://api.example.test/api/v1/products", () =>
        HttpResponse.json({ detail: "Authentication required." }, { status: 401 }),
      ),
    );
    const unauthorizedApi = api({ onUnauthorized });
    await expect(
      unauthorizedApi.unwrap(unauthorizedApi.client.GET("/api/v1/products")),
    ).rejects.toMatchObject({ kind: "unauthenticated", status: 401 });
    expect(onUnauthorized).toHaveBeenCalledOnce();

    server.use(
      http.get("https://api.example.test/api/v1/products", () =>
        HttpResponse.json({ detail: "Permission denied." }, { status: 403 }),
      ),
    );
    const forbiddenApi = api({ onUnauthorized });
    await expect(
      forbiddenApi.unwrap(forbiddenApi.client.GET("/api/v1/products")),
    ).rejects.toMatchObject({ kind: "forbidden", status: 403 });
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("normalizes validation and unavailable errors without exposing payloads", async () => {
    server.use(
      http.get("https://api.example.test/api/v1/products", () =>
        HttpResponse.json(
          { detail: [{ loc: ["query", "value"], msg: "private detail" }] },
          { status: 422, headers: { "X-Request-ID": "request-422" } },
        ),
      ),
    );
    const validationApi = api();
    await expect(
      validationApi.unwrap(validationApi.client.GET("/api/v1/products")),
    ).rejects.toEqual(
      expect.objectContaining({
        kind: "validation",
        message: "The request did not match the API contract.",
        requestId: "request-422",
      }),
    );

    server.use(
      http.get("https://api.example.test/api/v1/products", () => HttpResponse.error()),
    );
    const unavailableApi = api();
    await expect(
      unavailableApi.unwrap(unavailableApi.client.GET("/api/v1/products")),
    ).rejects.toBeInstanceOf(ApiError);
    await expect(
      unavailableApi.unwrap(unavailableApi.client.GET("/api/v1/products")),
    ).rejects.toMatchObject({ kind: "unavailable" });
  });
});
