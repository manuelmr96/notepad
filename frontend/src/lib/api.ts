import { useAuth } from "@/stores/auth";

/**
 * Thin fetch wrapper for the Notepad API.
 *
 * Contract (consumed by Plans 05/06):
 *   apiFetch(path, init?)  -> Promise<Response>
 *   bootstrapAuth()        -> Promise<void>
 *
 * Behaviour:
 * - Prefixes every request with `/api` (same-origin via the Vite dev proxy in
 *   dev and the nginx reverse proxy in prod — no CORS, refresh cookie rides along).
 * - Attaches the in-memory access token as `Authorization: Bearer <token>`.
 * - Sends `credentials: "include"` on EVERY call so the httpOnly refresh cookie is
 *   transmitted (Pitfall 3).
 * - On a 401 for a non-auth route, performs ONE silent refresh via /auth/refresh
 *   (Pattern 5). On success it stores the new token and retries the original
 *   request once; on failure it clears the session.
 */

const API_PREFIX = "/api";

interface RefreshResponse {
  access_token: string;
}

function isRefreshResponse(value: unknown): value is RefreshResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).access_token === "string"
  );
}

function buildInit(init: RequestInit, token: string | null): RequestInit {
  return {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  };
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = useAuth.getState().accessToken;
  let res = await fetch(`${API_PREFIX}${path}`, buildInit(init, token));

  if (res.status === 401 && !path.startsWith("/auth/")) {
    const refreshed = await fetch(`${API_PREFIX}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (refreshed.ok) {
      const data: unknown = await refreshed.json();
      if (isRefreshResponse(data)) {
        useAuth.getState().setToken(data.access_token);
        res = await fetch(`${API_PREFIX}${path}`, buildInit(init, data.access_token));
      } else {
        useAuth.getState().clear();
      }
    } else {
      useAuth.getState().clear();
    }
  }

  return res;
}

/**
 * Called once on app boot to restore the session from the refresh cookie (AUTH-03).
 * Always flips `bootstrapped` true so the UI can stop blocking on the initial check.
 */
export async function bootstrapAuth(): Promise<void> {
  try {
    const res = await fetch(`${API_PREFIX}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (res.ok) {
      const data: unknown = await res.json();
      if (isRefreshResponse(data)) {
        useAuth.getState().setToken(data.access_token);
      }
    }
  } catch {
    // Network error on boot is non-fatal — user simply lands logged-out.
  } finally {
    useAuth.getState().setBootstrapped(true);
  }
}
