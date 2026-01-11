import { useEffect, type ReactNode } from "react";
import { bootstrapAuth } from "@/lib/api";
import { useAuth } from "@/stores/auth";

// Boot gate (AUTH-03, Pitfall 3): runs the silent /auth/refresh on mount and shows a spinner until it settles, so a refresh on a protected route doesn't bounce to /login.
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
