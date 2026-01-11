import { useAuth } from "@/stores/auth";

// Thin fetch wrapper for the Notepad API: prefixes /api (same-origin, no CORS), attaches the in-memory Bearer token, sends credentials:include for the refresh cookie (Pitfall 3), and on a 401 for a non-auth route does ONE silent /auth/refresh + retry, else clears the session (Pattern 5).

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

// Called once on app boot to restore the session from the refresh cookie (AUTH-03); always flips `bootstrapped` true so the UI stops blocking on the initial check.
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
