import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { useAutosave } from "./useAutosave";

// NOTE-06 autosave coverage: debounce coalescing, immediate flush(), and the idle->saving->saved transitions (plus "error" on a failed PATCH). fetch is mocked; fake timers drive the debounce.

const NOTE_ID = "note-1";
const DEBOUNCE_MS = 1000;

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  // seed the single-note cache so optimistic onMutate has a snapshot
  queryClient.setQueryData(["notes", NOTE_ID], {
    id: NOTE_ID,
    title: "",
    content: null,
    content_schema_version: 1,
    created_at: "",
    updated_at: "",
  });
  return createElement(QueryClientProvider, { client: queryClient }, children);
}

function mockOkFetch() {
  const fn = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({
      id: NOTE_ID,
      title: "x",
      content: null,
      content_schema_version: 1,
      created_at: "",
      updated_at: "",
    }),
  } as Response);
  vi.stubGlobal("fetch", fn);
  return fn;
}

function lastBody(fn: ReturnType<typeof vi.fn>): unknown {
  const calls = fn.mock.calls;
  const init = calls[calls.length - 1]?.[1] as RequestInit | undefined;
  return init?.body ? JSON.parse(init.body as string) : undefined;
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  cleanup();
});

describe("useAutosave", () => {
  it("coalesces rapid keystrokes into a single PATCH with the latest value", async () => {
    const fetchFn = mockOkFetch();
    const { result } = renderHook(() => useAutosave(NOTE_ID, DEBOUNCE_MS), {
      wrapper,
    });

    act(() => {
      result.current.onChange({ title: "a" });
      result.current.onChange({ title: "ab" });
      result.current.onChange({ title: "abc" });
    });

    // Before the debounce elapses, nothing has fired.
    expect(fetchFn).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(DEBOUNCE_MS);
    });

    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(lastBody(fetchFn)).toEqual({ title: "abc" });
  });

  it("flush() fires immediately without waiting for the debounce", async () => {
    const fetchFn = mockOkFetch();
    const { result } = renderHook(() => useAutosave(NOTE_ID, DEBOUNCE_MS), {
      wrapper,
    });

    act(() => {
      result.current.onChange({ title: "hi" });
    });
    expect(fetchFn).not.toHaveBeenCalled();

    await act(async () => {
      result.current.flush();
    });

    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(lastBody(fetchFn)).toEqual({ title: "hi" });
  });

  it("transitions status idle -> saving -> saved", async () => {
    let resolveFetch: (v: Response) => void = () => {};
    const fetchFn = vi.fn().mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve;
        }),
    );
    vi.stubGlobal("fetch", fetchFn);

    const { result } = renderHook(() => useAutosave(NOTE_ID, DEBOUNCE_MS), {
      wrapper,
    });

    expect(result.current.status).toBe("idle");

    await act(async () => {
      result.current.onChange({ title: "z" });
      result.current.flush();
      // let useMutation flip isPending -> true
      await vi.advanceTimersByTimeAsync(0);
    });

    // mutation is in-flight (fetch promise unresolved)
    expect(result.current.status).toBe("saving");

    await act(async () => {
      resolveFetch({
        ok: true,
        status: 200,
        json: async () => ({
          id: NOTE_ID,
          title: "z",
          content: null,
          content_schema_version: 1,
          created_at: "",
          updated_at: "",
        }),
      } as Response);
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(result.current.status).toBe("saved");
  });

  it("yields status 'error' when the PATCH fails", async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    } as Response);
    vi.stubGlobal("fetch", fetchFn);

    const { result } = renderHook(() => useAutosave(NOTE_ID, DEBOUNCE_MS), {
      wrapper,
    });

    await act(async () => {
      result.current.onChange({ title: "boom" });
      result.current.flush();
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(result.current.status).toBe("error");
  });
});
