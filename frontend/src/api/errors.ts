export type ApiErrorKind =
  | "unauthenticated"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "validation"
  | "unavailable"
  | "unexpected";

export interface ApiResponseMetadata {
  readonly requestId?: string;
  readonly revision?: string;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly requestId: string | undefined;
  readonly revision: string | undefined;

  constructor(
    message: string,
    options: ApiResponseMetadata & {
      readonly kind: ApiErrorKind;
      readonly status?: number;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.kind = options.kind;
    this.status = options.status;
    this.requestId = options.requestId;
    this.revision = options.revision;
  }
}

function boundedHeader(response: Response, name: string): string | undefined {
  const value = response.headers.get(name)?.trim();
  return value !== undefined && value !== "" && value.length <= 128 ? value : undefined;
}

function boundedDetail(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null) {
    return undefined;
  }
  const detail = (error as Record<string, unknown>).detail;
  if (typeof detail === "string") {
    const normalized = detail.trim();
    return normalized === "" ? undefined : normalized.slice(0, 280);
  }
  if (Array.isArray(detail)) {
    return "The request did not match the API contract.";
  }
  return undefined;
}

export function apiErrorFromResponse(response: Response, error: unknown): ApiError {
  const requestId = boundedHeader(response, "x-request-id");
  const revision = boundedHeader(response, "x-opsmind-revision");
  const metadata: ApiResponseMetadata = {
    ...(requestId ? { requestId } : {}),
    ...(revision ? { revision } : {}),
  };
  const detail = boundedDetail(error);
  const options = { ...metadata, status: response.status };
  switch (response.status) {
    case 401:
      return new ApiError("Your session is no longer valid. Sign in again.", {
        ...options,
        kind: "unauthenticated",
      });
    case 403:
      return new ApiError("You do not have permission for this action.", {
        ...options,
        kind: "forbidden",
      });
    case 404:
      return new ApiError(detail ?? "The requested resource was not found.", {
        ...options,
        kind: "not_found",
      });
    case 409:
      return new ApiError(detail ?? "The request conflicts with current state.", {
        ...options,
        kind: "conflict",
      });
    case 422:
      return new ApiError(detail ?? "The request did not match the API contract.", {
        ...options,
        kind: "validation",
      });
    case 502:
    case 503:
    case 504:
      return new ApiError("The OpsMind API is waking or temporarily unavailable.", {
        ...options,
        kind: "unavailable",
      });
    default:
      return new ApiError("OpsMind could not complete the request.", {
        ...options,
        kind: "unexpected",
      });
  }
}

export function networkApiError(): ApiError {
  return new ApiError("The OpsMind API is waking or temporarily unavailable.", {
    kind: "unavailable",
  });
}
