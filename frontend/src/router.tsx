import { createBrowserRouter, Navigate, type RouteObject } from "react-router-dom";
import { RequireAuth } from "@/components/RequireAuth";
import { AppShell } from "@/components/AppShell";
import { NoteEditor } from "@/features/notes/NoteEditor";
import { NoteEmptyState } from "@/features/notes/NoteEmptyState";
import { useAuth } from "@/stores/auth";
import LoginPage from "@/features/auth/LoginPage";
import RegisterPage from "@/features/auth/RegisterPage";

// Application router — React Router 7 in LIBRARY/SPA mode (createBrowserRouter, NOT framework/SSR mode, per CLAUDE.md). Routes (D-09/D-10/D-11/D-16): /login + /register (redirect to / if authed), / -> RequireAuth -> AppShell with index empty state and /notes/:id editor, * -> /. AuthGate has settled the boot refresh before this renders.

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
        // The protected two-pane notes shell; its Outlet renders the editor or the "Select or create a note" empty state.
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
