import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./api/errors";

export const queryKeys = {
  all: ["opsmind"] as const,
  products: () => [...queryKeys.all, "products"] as const,
  product: (productId: string) => [...queryKeys.products(), productId] as const,
  inventory: (productId: string) =>
    [...queryKeys.product(productId), "inventory"] as const,
  demand: (productId: string) => [...queryKeys.product(productId), "demand"] as const,
  recommendations: () => [...queryKeys.all, "recommendations"] as const,
  recommendation: (recommendationId: string) =>
    [...queryKeys.recommendations(), recommendationId] as const,
};

export function shouldRetryRead(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) {
    return false;
  }
  if (error instanceof ApiError) {
    return error.kind === "unavailable" || error.kind === "unexpected";
  }
  return true;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: shouldRetryRead,
        retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 2_000),
        staleTime: 30_000,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}
