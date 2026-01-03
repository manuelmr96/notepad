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
  /** Set true after the initial /auth/refresh on app boot resolves (AUTH-03). */
  bootstrapped: boolean;
  setToken: (t: string | null) => void;
  setBootstrapped: (b: boolean) => void;
  clear: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  accessToken: null,
  bootstrapped: false,
  setToken: (accessToken) => set({ accessToken }),
  setBootstrapped: (bootstrapped) => set({ bootstrapped }),
  clear: () => set({ accessToken: null }),
}));
