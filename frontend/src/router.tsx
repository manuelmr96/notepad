import { createBrowserRouter, Navigate, type RouteObject } from "react-router-dom";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShellPlaceholder } from "@/components/AppShellPlaceholder";
import { useAuth } from "@/stores/auth";
import LoginPage from "@/features/auth/LoginPage";
import RegisterPage from "@/features/auth/RegisterPage";

/**
 * Application router — React Router 7 in LIBRARY / SPA mode (`createBrowserRouter`).
 *
 * This is intentionally NOT the framework/SSR (`react-router.config`) mode — see
 * CLAUDE.md: "v7 (the merged Remix/RR) in SPA/library mode (`createBrowserRouter`)
 * — do NOT adopt its framework/SSR mode."
 *
 * Route map (D-09/D-10/D-11):
 *   /login     -> LoginPage     (redirects to / if already authenticated)
 *   /register  -> RegisterPage  (redirects to / if already authenticated)
 *   /          -> RequireAuth -> app shell (logged-out users bounce to /login)
 *   *          -> redirect to /
 *
 * The AuthGate (mounted in main.tsx) has already resolved the boot refresh
 * before this router renders, so redirect decisions see a settled session.
 */

/** Bounce already-authenticated users away from the auth screens. */
function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  const accessToken = useAuth((s) => s.accessToken);
  if (accessToken !== null) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

const routes: RouteObject[] = [
  {
    path: "/login",
    element: (
      <RedirectIfAuthed>
        <LoginPage />
      </RedirectIfAuthed>
    ),
  },
  {
    path: "/register",
    element: (
      <RedirectIfAuthed>
        <RegisterPage />
      </RedirectIfAuthed>
    ),
  },
  {
    path: "/",
    element: <RequireAuth />,
    children: [
      {
        index: true,
        // TODO(Plan 07): replace <AppShellPlaceholder /> with the real two-pane
        // notes shell (collapsible sidebar list + editor pane). The shell's user
        // menu will call the `useLogout` hook exported from features/auth.
        element: <AppShellPlaceholder />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
];

export const router = createBrowserRouter(routes);
