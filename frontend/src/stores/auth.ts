import { create } from "zustand";

// Auth store — holds the short-lived access token in memory ONLY (T-02-01: no browser storage, no storage middleware); the long-lived refresh token lives in an httpOnly cookie JS cannot read.
interface AuthState {
  accessToken: string | null;
  // Email captured at login/register for the sidebar user menu (D-04); not derived from the token and not restored after a boot refresh (falls back to a generic label). Display-only, memory-only (T-02-01).
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
