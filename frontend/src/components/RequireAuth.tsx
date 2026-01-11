import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/stores/auth";

// Protected-route guard (D-11): redirects to /login when the in-memory token is absent, else renders <Outlet />. UX only (T-06-03) — real enforcement is server-side.
export function RequireAuth() {
  const accessToken = useAuth((s) => s.accessToken);

  if (accessToken === null) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
