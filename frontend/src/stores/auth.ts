import { create } from "zustand";

/**
 * Auth store — holds the short-lived access token in memory ONLY.
 *
 * Security requirement (CLAUDE.md browser-storage ban + threat T-02-01): the
 * access token is never written to any browser storage and this store uses NO
 * storage middleware (memory only). The long-lived refresh token lives in
 * an httpOnly Secure SameSite cookie set by the server, which JS cannot read.
 */
interface AuthState {
  accessToken: string | null;
  /**
   * The signed-in user's email, captured at login/register for the sidebar user
   * menu (D-04). It is NOT derived from the access token (whose `sub` is the user
   * UUID, and there is no /auth/me endpoint in Phase 1). After a silent boot
   * refresh the token is restored but the email is not, so the user menu falls
   * back to a generic identity label — purely a display concern, never security.
   * Like the token, the email is memory-only (no browser storage, T-02-01).
   */
  email: string | null;
  /** Set true after the initial /auth/refresh on app boot resolves (AUTH-03). */
  bootstrapped: boolean;
  setToken: (t: string | null) => void;
  setEmail: (e: string | null) => void;
  setBootstrapped: (b: boolean) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  accessToken: null,
  email: null,
  bootstrapped: false,
  setToken: (accessToken) => set({ accessToken }),
  setEmail: (email) => set({ email }),
  setBootstrapped: (bootstrapped) => set({ bootstrapped }),
  clear: () => set({ accessToken: null, email: null }),
}));
