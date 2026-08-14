import createClient, { type Client } from "openapi-fetch";

import type { paths } from "./generated/schema";
import {
  apiErrorFromResponse,
  networkApiError,
  type ApiResponseMetadata,
} from "./errors";

interface ApiClientOptions {
  readonly baseUrl: string;
  readonly getAccessToken: () => Promise<string | undefined>;
  readonly onUnauthorized: () => Promise<void>;
  readonly requestIdFactory?: () => string;
  readonly fetch?: (request: Request) => Promise<Response>;
}

export interface ApiSuccess<T> extends ApiResponseMetadata {
  readonly data: T;
}

interface FetchResult<T> {
  readonly data?: T;
  readonly error?: unknown;
  readonly response: Response;
}

export interface OpsMindApi {
  readonly client: Client<paths>;
  readonly unwrap: <T>(request: Promise<FetchResult<T>>) => Promise<ApiSuccess<T>>;
}

function metadata(response: Response): ApiResponseMetadata {
  const requestId = response.headers.get("x-request-id")?.trim();
  const revision = response.headers.get("x-opsmind-revision")?.trim();
  return {
    ...(requestId && requestId.length <= 128 ? { requestId } : {}),
    ...(revision && revision.length <= 128 ? { revision } : {}),
  };
}

export function createOpsMindApi(options: ApiClientOptions): OpsMindApi {
  const requestIdFactory = options.requestIdFactory ?? (() => crypto.randomUUID());
  const client = createClient<paths>({
    baseUrl: options.baseUrl,
    credentials: "omit",
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });

  client.use({
    async onRequest({ request }) {
      const headers = new Headers(request.headers);
      headers.set("Accept", "application/json");
      if (!headers.has("X-Request-ID")) {
        headers.set("X-Request-ID", requestIdFactory());
      }
      const token = await options.getAccessToken();
      if (token !== undefined) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return new Request(request, { credentials: "omit", headers });
    },
    async onResponse({ response }) {
      if (response.status === 401) {
        await options.onUnauthorized();
      }
      return response;
    },
  });

  return {
    client,
    async unwrap<T>(request: Promise<FetchResult<T>>): Promise<ApiSuccess<T>> {
      let result: FetchResult<T>;
      try {
        result = await request;
      } catch {
        throw networkApiError();
      }
      if (result.error !== undefined || result.data === undefined) {
        throw apiErrorFromResponse(result.response, result.error);
      }
      return { data: result.data, ...metadata(result.response) };
    },
  };
}
