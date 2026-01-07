import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/stores/auth";

/**
 * Protected-route guard (D-11).
 *
 * Reads the in-memory access token; when absent it redirects to `/login`
 * (`replace` so the protected URL is not left in history). Otherwise it renders
 * the matched child route via <Outlet />.
 *
 * NOTE (threat T-06-03): this is UX only — hiding routes is NOT a security
 * boundary. Real enforcement is server-side (`get_current_user`, Plan 04/05).
 * The AuthGate boot refresh has already resolved by the time this runs, so the
 * token reflects a settled session (no premature redirect).
 */
export function RequireAuth() {
  const accessToken = useAuth((s) => s.accessToken);

  if (accessToken === null) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
