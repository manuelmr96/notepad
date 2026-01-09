import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/stores/auth";
import type { LoginValues, RegisterValues } from "./schema";

/**
 * Auth mutations wiring the Plan 02 api wrapper to the Plan 04 endpoints.
 *
 * - useLogin    -> POST /auth/login    (401 -> form-level "Incorrect email or password.")
 * - useRegister -> POST /auth/register (409 -> "An account with this email already exists.")
 * - useLogout   -> POST /auth/logout, then clear in-memory token + redirect (AUTH-04, T-06-04)
 *
 * On success login/register store the access token (auto-login on register, D-10)
 * and the caller navigates to "/". Non-2xx responses are mapped to a typed
 * `AuthError` whose `message` is the exact UI-SPEC copy for form-level display.
 *
 * Security (T-06-01): the token is only ever passed to the in-memory store —
 * never written to any browser storage here.
 * Security (T-06-02): login surfaces the single generic credential error.
 */

const LOGIN_FAILED = "Incorrect email or password.";
const EMAIL_EXISTS = "An account with this email already exists. Log in instead.";
const GENERIC_ERROR = "Something went wrong. Please try again.";

/** Typed error carrying the form-level message to render in the destructive region. */
export class AuthError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "AuthError";
  }
}

interface TokenBody {
  access_token: string;
}

function isTokenBody(value: unknown): value is TokenBody {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).access_token === "string"
  );
}

async function postCredentials(
  path: "/auth/login" | "/auth/register",
  values: LoginValues | RegisterValues,
): Promise<void> {
  const res = await apiFetch(path, {
    method: "POST",
    body: JSON.stringify(values),
  });

  if (!res.ok) {
    if (path === "/auth/login" && res.status === 401) {
      throw new AuthError(LOGIN_FAILED, res.status);
    }
    if (path === "/auth/register" && res.status === 409) {
      throw new AuthError(EMAIL_EXISTS, res.status);
    }
    throw new AuthError(GENERIC_ERROR, res.status);
  }

  const data: unknown = await res.json();
  if (!isTokenBody(data)) {
    throw new AuthError(GENERIC_ERROR, res.status);
  }

  // Memory-only store (no persisted token) — T-06-01.
  useAuth.getState().setToken(data.access_token);
  // Capture the email for the sidebar user menu (D-04) — display-only, memory-only.
  useAuth.getState().setEmail(values.email);
}

export function useLogin() {
  return useMutation<void, AuthError, LoginValues>({
    mutationFn: (values) => postCredentials("/auth/login", values),
  });
}

export function useRegister() {
  return useMutation<void, AuthError, RegisterValues>({
    // Auto-login on success (D-10): setToken happens in postCredentials.
    mutationFn: (values) => postCredentials("/auth/register", values),
  });
}

/**
 * Logout (AUTH-04, T-06-04): revoke the refresh token server-side, then clear the
 * in-memory access token and return to /login. The store is cleared even if the
 * network call fails so the client never shows a stale session.
 */
export function useLogout() {
  const navigate = useNavigate();
  return useMutation<void, Error, void>({
    mutationFn: async () => {
      try {
        await apiFetch("/auth/logout", { method: "POST" });
      } finally {
        useAuth.getState().clear();
      }
    },
    onSuccess: () => {
      navigate("/login", { replace: true });
    },
  });
}
