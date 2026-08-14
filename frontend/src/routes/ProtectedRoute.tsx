import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/context";
import { LoadingState } from "../components/States";

export function ProtectedRoute() {
  const auth = useAuth();
  const location = useLocation();
  if (auth.status === "loading") {
    return (
      <main className="centered-page" id="main-content">
        <LoadingState label="Restoring your OpsMind session" />
      </main>
    );
  }
  if (auth.status === "unauthenticated") {
    return (
      <Navigate
        replace
        state={{ from: `${location.pathname}${location.search}` }}
        to="/login"
      />
    );
  }
  return <Outlet />;
}
