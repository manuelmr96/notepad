import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "@/stores/auth";
import { apiFetch } from "./api";

// API-01..04: apiFetch — Bearer attachment, 401 silent-refresh-and-retry, failed refresh session clear, auth-path bypass.

beforeEach(() => {
  useAuth.setState({ accessToken: null, email: null, bootstrapped: false });
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiFetch", () => {
  it("attaches Authorization header and credentials:include when a token is set", async () => {
    useAuth.setState({ accessToken: "my-token", email: null, bootstrapped: true });

    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    } as Response);
    vi.stubGlobal("fetch", fetchFn);

    await apiFetch("/notes");

    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFn.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/notes");
    expect((init.headers as Record<string, string>)["Authorization"]).toBe("Bearer my-token");
    expect(init.credentials).toBe("include");
  });

  it("on 401 for a non-auth route, calls POST /api/auth/refresh, stores new token, and retries with new Bearer", async () => {
    useAuth.setState({ accessToken: "old-token", email: null, bootstrapped: true });

    const fetchFn = vi
      .fn()
      // First call: original request → 401
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({}),
      } as Response)
      // Second call: refresh → ok with new token
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "new" }),
      } as Response)
      // Third call: retry with new token → ok
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: "1" }),
      } as Response);

    vi.stubGlobal("fetch", fetchFn);

    await apiFetch("/notes");

    // fetch must be called exactly 3 times
    expect(fetchFn).toHaveBeenCalledTimes(3);

    // Second call must be the refresh
    const [refreshUrl, refreshInit] = fetchFn.mock.calls[1] as [string, RequestInit];
    expect(refreshUrl).toBe("/api/auth/refresh");
    expect(refreshInit?.method).toBe("POST");

    // New token is stored in the auth store
    expect(useAuth.getState().accessToken).toBe("new");

    // Third call (retry) carries the new Bearer token
    const [retryUrl, retryInit] = fetchFn.mock.calls[2] as [string, RequestInit];
    expect(retryUrl).toBe("/api/notes");
    expect((retryInit.headers as Record<string, string>)["Authorization"]).toBe("Bearer new");
  });

  it("on a failed refresh, clears the session and does NOT retry", async () => {
    useAuth.setState({ accessToken: "old-token", email: null, bootstrapped: true });

    const fetchFn = vi
      .fn()
      // First call: original → 401
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({}),
      } as Response)
      // Second call: refresh → failed
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({}),
      } as Response);

    vi.stubGlobal("fetch", fetchFn);

    await apiFetch("/notes");

    // Only 2 calls: original + failed refresh; NO retry
    expect(fetchFn).toHaveBeenCalledTimes(2);

    // Session cleared
    expect(useAuth.getState().accessToken).toBeNull();
  });

  it("a 401 on a path starting with /auth/ does NOT trigger a refresh", async () => {
    useAuth.setState({ accessToken: "some-token", email: null, bootstrapped: true });

    const fetchFn = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({}),
    } as Response);
    vi.stubGlobal("fetch", fetchFn);

    await apiFetch("/auth/login");

    // Only 1 call — no refresh attempt
    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url] = fetchFn.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/auth/login");
  });
});
