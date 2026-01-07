import { useEffect, type ReactNode } from "react";
import { bootstrapAuth } from "@/lib/api";
import { useAuth } from "@/stores/auth";

/**
 * Boot gate (AUTH-03, Pitfall 3).
 *
 * On first mount it runs `bootstrapAuth()` — the silent `/auth/refresh` that
 * restores the session from the httpOnly refresh cookie. Until that resolves
 * (`bootstrapped === false`) it renders a minimal centered spinner instead of
 * the routes. This guarantees the refresh has settled BEFORE any router
 * redirect decision runs, so a page refresh on a protected route does not
 * briefly bounce the user to `/login`.
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const bootstrapped = useAuth((s) => s.bootstrapped);

  useEffect(() => {
    if (!useAuth.getState().bootstrapped) {
      void bootstrapAuth();
    }
  }, []);

  if (!bootstrapped) {
    return (
      <div
        className="flex min-h-svh items-center justify-center bg-background"
        role="status"
        aria-label="Loading"
      >
        <div
          className="size-6 animate-spin rounded-full border-2 border-muted border-t-foreground"
          aria-hidden="true"
        />
      </div>
    );
  }

  return <>{children}</>;
}
