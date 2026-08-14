import { Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { CallbackPage } from "./routes/CallbackPage";
import {
  ForbiddenPage,
  NotFoundPage,
  OverviewPage,
  ProductDetailPage,
  ProductsPage,
  RecommendationDetailPage,
  RecommendationsPage,
  UnavailablePage,
} from "./routes/FoundationPages";
import { LoginPage } from "./routes/LoginPage";
import { ProtectedRoute } from "./routes/ProtectedRoute";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<LoginPage />} path="/login" />
      <Route element={<CallbackPage />} path="/auth/callback" />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route element={<OverviewPage />} index />
          <Route element={<ProductsPage />} path="products" />
          <Route element={<ProductDetailPage />} path="products/:productId" />
          <Route element={<RecommendationsPage />} path="recommendations" />
          <Route
            element={<RecommendationDetailPage />}
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
