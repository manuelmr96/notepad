import { Button } from "@/components/ui/button";
import { useLogout } from "@/features/auth/useAuthMutations";

/**
 * TEMPORARY app root for Phase 1 Plan 06.
 *
 * TODO(Plan 07): replace this entirely with the real two-pane notes shell
 * (collapsible sidebar note list + editor pane). Plan 07's user menu will call
 * the same `useLogout` hook this placeholder wires up.
 *
 * For now it confirms the protected route renders for an authenticated user and
 * offers a logout affordance (AUTH-04) so the revoke + redirect flow is
 * exercisable end-to-end.
 */
export function AppShellPlaceholder() {
  const logout = useLogout();

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-4 bg-background text-foreground">
      <p data-testid="app-shell-placeholder" className="text-sm text-muted-foreground">
        Logged in — Notepad shell mounts here (Plan 07).
      </p>
      <Button
        variant="outline"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        Log out
      </Button>
    </div>
  );
}
