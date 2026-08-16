import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "../api/context";
import type { components } from "../api/generated/schema";
import { queryKeys } from "../query";

export type Product = components["schemas"]["ProductResponse"];
export type ProductCreate = components["schemas"]["ProductCreateRequest"];
export type Inventory = components["schemas"]["InventoryResponse"];
export type InventorySet = components["schemas"]["InventorySetRequest"];
export type DemandObservation = components["schemas"]["DemandObservationResponse"];
export type DemandBatch = components["schemas"]["DemandBatchCreate"];
export type Forecast = components["schemas"]["ForecastResponse"];
export type StockoutExposure = components["schemas"]["StockoutExposureResponse"];
export type ReorderRecommendation =
  components["schemas"]["ReorderRecommendationResponse"];
export type RecommendationReview =
  components["schemas"]["ReorderRecommendationReviewResponse"];
export type ReviewStatus = components["schemas"]["RecommendationReviewStatus"];
export type AuditHistory = components["schemas"]["RecommendationAuditHistoryResponse"];
export type Approval = components["schemas"]["ApproveRecommendationRequest"];
export type Rejection = components["schemas"]["RejectRecommendationRequest"];

export interface CalculationOptions {
  readonly lookbackObservations: number;
  readonly asOfDate?: string;
}

export function useProducts() {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.products(),
    queryFn: async () => (await api.unwrap(api.client.GET("/api/v1/products"))).data,
  });
}

export function useCreateProduct() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProductCreate) =>
      (await api.unwrap(api.client.POST("/api/v1/products", { body }))).data,
    onSuccess: async () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.products() }),
  });
}

export function useProduct(productId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.product(productId),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/products/{product_id}", {
            params: { path: { product_id: productId } },
          }),
        )
      ).data,
    enabled: productId !== "",
  });
}

export function useInventory(productId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.inventory(productId),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/products/{product_id}/inventory", {
            params: { path: { product_id: productId } },
          }),
        )
      ).data,
  });
}

export function useSetInventory(productId: string) {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: InventorySet) =>
      (
        await api.unwrap(
          api.client.PUT("/api/v1/products/{product_id}/inventory", {
            params: { path: { product_id: productId } },
            body,
          }),
        )
      ).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.inventory(productId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.calculations(productId) }),
      ]);
    },
  });
}

export function useDemand(productId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.demand(productId),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/products/{product_id}/demand", {
            params: { path: { product_id: productId } },
          }),
        )
      ).data,
  });
}

export function useAppendDemand(productId: string) {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: DemandBatch) =>
      (
        await api.unwrap(
          api.client.POST("/api/v1/products/{product_id}/demand", {
            params: { path: { product_id: productId } },
            body,
          }),
        )
      ).data,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.demand(productId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.calculations(productId) }),
      ]);
    },
  });
}

function calculationQuery(options: CalculationOptions) {
  return {
    lookback_observations: options.lookbackObservations,
    ...(options.asOfDate ? { as_of_date: options.asOfDate } : {}),
  };
}

export function useForecast(
  productId: string,
  options: CalculationOptions & { readonly horizonDays: number },
) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.forecast(productId, options),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/products/{product_id}/forecast", {
            params: {
              path: { product_id: productId },
              query: {
                ...calculationQuery(options),
                horizon_days: options.horizonDays,
              },
            },
          }),
        )
      ).data,
  });
}

export function useExposure(productId: string, options: CalculationOptions) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.exposure(productId, options),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/products/{product_id}/stockout-exposure", {
            params: {
              path: { product_id: productId },
              query: calculationQuery(options),
            },
          }),
        )
      ).data,
  });
}

export function useReorder(productId: string, options: CalculationOptions) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.reorder(productId, options),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/products/{product_id}/reorder-recommendation", {
            params: {
              path: { product_id: productId },
              query: calculationQuery(options),
            },
          }),
        )
      ).data,
  });
}

export function usePersistRecommendation(productId: string) {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (options: CalculationOptions) =>
      (
        await api.unwrap(
          api.client.POST("/api/v1/products/{product_id}/reorder-recommendations", {
            params: {
              path: { product_id: productId },
              query: calculationQuery(options),
            },
          }),
        )
      ).data,
    onSuccess: async (review) => {
      queryClient.setQueryData(
        queryKeys.recommendation(review.recommendation_id),
        review,
      );
      await queryClient.invalidateQueries({
        queryKey: queryKeys.recommendationLists(),
      });
    },
  });
}

export interface RecommendationFilters {
  readonly productId?: string;
  readonly reviewStatus?: ReviewStatus;
}

export function useRecommendations(filters: RecommendationFilters = {}) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.recommendationList(filters),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/reorder-recommendations", {
            params: {
              query: {
                ...(filters.productId ? { product_id: filters.productId } : {}),
                ...(filters.reviewStatus
                  ? { review_status: filters.reviewStatus }
                  : {}),
              },
            },
          }),
        )
      ).data,
  });
}

export function useRecommendation(recommendationId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.recommendation(recommendationId),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET("/api/v1/reorder-recommendations/{recommendation_id}", {
            params: { path: { recommendation_id: recommendationId } },
          }),
        )
      ).data,
  });
}

export function useAuditHistory(recommendationId: string) {
  const api = useApi();
  return useQuery({
    queryKey: queryKeys.audit(recommendationId),
    queryFn: async () =>
      (
        await api.unwrap(
          api.client.GET(
            "/api/v1/reorder-recommendations/{recommendation_id}/audit-events",
            { params: { path: { recommendation_id: recommendationId } } },
          ),
        )
      ).data,
  });
}

function useDecision(recommendationId: string, decision: "approve" | "reject") {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Approval | Rejection) => {
      const request =
        decision === "approve"
          ? api.client.POST(
              "/api/v1/reorder-recommendations/{recommendation_id}/approve",
              {
                params: { path: { recommendation_id: recommendationId } },
                body: body as Approval,
              },
            )
          : api.client.POST(
              "/api/v1/reorder-recommendations/{recommendation_id}/reject",
              {
                params: { path: { recommendation_id: recommendationId } },
                body: body as Rejection,
              },
            );
      return (await api.unwrap(request)).data;
    },
    onSuccess: async (review) => {
      queryClient.setQueryData(queryKeys.recommendation(recommendationId), review);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.recommendationLists() }),
        queryClient.invalidateQueries({ queryKey: queryKeys.audit(recommendationId) }),
      ]);
    },
  });
}

export function useApproveRecommendation(recommendationId: string) {
  return useDecision(recommendationId, "approve");
}

export function useRejectRecommendation(recommendationId: string) {
  return useDecision(recommendationId, "reject");
}
