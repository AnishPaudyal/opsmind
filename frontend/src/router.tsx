import { lazy, Suspense, type ReactNode } from "react";
import { Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/States";
import { CallbackPage } from "./routes/CallbackPage";
import { ForbiddenPage, NotFoundPage, UnavailablePage } from "./routes/FoundationPages";
import { LoginPage } from "./routes/LoginPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";

const OverviewPage = lazy(async () => ({
  default: (await import("./routes/OperationalPages")).OverviewPage,
}));
const ProductsPage = lazy(async () => ({
  default: (await import("./routes/OperationalPages")).ProductsPage,
}));
const ProductDetailPage = lazy(async () => ({
  default: (await import("./routes/OperationalPages")).ProductDetailPage,
}));
const RecommendationsPage = lazy(async () => ({
  default: (await import("./routes/OperationalPages")).RecommendationsPage,
}));
const RecommendationDetailPage = lazy(async () => ({
  default: (await import("./routes/OperationalPages")).RecommendationDetailPage,
}));

function DeferredRoute({ children }: { readonly children: ReactNode }) {
  return (
    <Suspense fallback={<LoadingState label="Loading operational workspace" />}>
      {children}
    </Suspense>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<LoginPage />} path="/login" />
      <Route element={<CallbackPage />} path="/auth/callback" />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route
            element={
              <DeferredRoute>
                <OverviewPage />
              </DeferredRoute>
            }
            index
          />
          <Route
            element={
              <DeferredRoute>
                <ProductsPage />
              </DeferredRoute>
            }
            path="products"
          />
          <Route
            element={
              <DeferredRoute>
                <ProductDetailPage />
              </DeferredRoute>
            }
            path="products/:productId"
          />
          <Route
            element={
              <DeferredRoute>
                <RecommendationsPage />
              </DeferredRoute>
            }
            path="recommendations"
          />
          <Route
            element={
              <DeferredRoute>
                <RecommendationDetailPage />
              </DeferredRoute>
            }
            path="recommendations/:recommendationId"
          />
          <Route element={<ForbiddenPage />} path="forbidden" />
          <Route element={<UnavailablePage />} path="unavailable" />
          <Route element={<NotFoundPage />} path="*" />
        </Route>
      </Route>
    </Routes>
  );
}
