import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import LoginPage from "./LoginPage";
import { useAuth } from "@/stores/auth";

/**
 * LoginPage coverage (Task 3): inline validation (invalid email, short
 * password), the form-level invalid-credentials error on a 401, and the
 * token-set success path. `fetch` is mocked so no network is hit; assertions on
 * the auth store confirm the success path stores the access token.
 */

function renderLoginPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/login"]}>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetch(response: { ok: boolean; status: number; body?: unknown }) {
  const fn = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: async () => response.body ?? {},
  } as Response);
  vi.stubGlobal("fetch", fn);
  return fn;
}

function fillForm(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: email },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: password },
  });
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: /log in/i }));
}

beforeEach(() => {
  // Reset the in-memory auth store between tests.
  useAuth.setState({ accessToken: null, bootstrapped: false });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("LoginPage", () => {
  it("renders the heading and a link to sign up", () => {
    mockFetch({ ok: true, status: 200, body: { access_token: "x" } });
    renderLoginPage();
    expect(
      screen.getByRole("heading", { name: "Log in" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute(
      "href",
      "/register",
    );
  });

  it("shows an inline error for an invalid email", async () => {
    mockFetch({ ok: true, status: 200, body: { access_token: "x" } });
    renderLoginPage();
    fillForm("not-an-email", "password123");
    submit();
    expect(
      await screen.findByText("Enter a valid email address."),
    ).toBeInTheDocument();
  });

  it("shows an inline error for a short password", async () => {
    mockFetch({ ok: true, status: 200, body: { access_token: "x" } });
    renderLoginPage();
    fillForm("user@example.com", "short");
    submit();
    expect(
      await screen.findByText("Password must be at least 8 characters."),
    ).toBeInTheDocument();
  });

  it("shows the form-level error on a 401", async () => {
    mockFetch({ ok: false, status: 401, body: {} });
    renderLoginPage();
    fillForm("user@example.com", "password123");
    submit();
    expect(
      await screen.findByText("Incorrect email or password."),
    ).toBeInTheDocument();
    expect(useAuth.getState().accessToken).toBeNull();
  });

  it("stores the access token on a successful login", async () => {
    mockFetch({ ok: true, status: 200, body: { access_token: "tok-123" } });
    renderLoginPage();
    fillForm("user@example.com", "password123");
    submit();
    await waitFor(() =>
      expect(useAuth.getState().accessToken).toBe("tok-123"),
    );
    expect(
      screen.queryByText("Incorrect email or password."),
    ).not.toBeInTheDocument();
  });
});
