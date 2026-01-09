import { createBrowserRouter, Navigate, type RouteObject } from "react-router-dom";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { NoteEditor } from "@/features/notes/NoteEditor";
import { NoteEmptyState } from "@/features/notes/NoteEmptyState";
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
 * Route map (D-09/D-10/D-11/D-16):
 *   /login        -> LoginPage     (redirects to / if already authenticated)
 *   /register     -> RegisterPage  (redirects to / if already authenticated)
 *   /             -> RequireAuth -> AppShell (two-pane notes shell)
 *     index       -> empty state ("Select or create a note", D-16)
 *     /notes/:id  -> NoteEditor (rendered in the shell Outlet)
 *   *             -> redirect to /
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
        // The protected two-pane notes shell; its Outlet renders the editor or
        // the "Select or create a note" empty state.
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <NoteEmptyState />,
          },
          {
            path: "notes/:id",
            element: <NoteEditor />,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
];

export const router = createBrowserRouter(routes);
