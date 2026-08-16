import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { App } from "./App";
import { publicConfig } from "./test/config-fixture";
import { FakeAuthService } from "./test/fake-auth";

describe("application routing and shell", () => {
  it.each([
    ["/", "Know what needs attention—and why."],
    ["/products", "Operational catalog"],
    ["/recommendations", "Decision review queue"],
  ])("renders the protected foundation route %s", async (path, heading) => {
    window.history.replaceState(null, "", path);
    render(
      <App authService={new FakeAuthService("authenticated")} config={publicConfig} />,
    );
    expect(await screen.findByRole("heading", { name: heading })).toBeVisible();
  });

  it("redirects an unauthenticated protected route and preserves its bounded path", async () => {
    window.history.replaceState(null, "", "/products?active=true");
    const auth = new FakeAuthService("unauthenticated");
    const user = userEvent.setup();
    render(<App authService={auth} config={publicConfig} />);

    expect(
      await screen.findByRole("heading", { name: /decisions backed/i }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: /continue with zitadel/i }));
    expect(auth.loginCalls).toEqual(["/products?active=true"]);
  });

  it("restores an authenticated session and renders deep-linked foundation pages", async () => {
    window.history.replaceState(null, "", "/products/product-123");
    const auth = new FakeAuthService("authenticated", ["opsmind.business.read"]);
    render(<App authService={auth} config={publicConfig} />);
    expect(await screen.findByText("Loading product workspace")).toBeVisible();
    expect(screen.getByText("1 mapped presentation role")).toBeVisible();
  });

  it("completes the callback and restores the intended route", async () => {
    window.history.replaceState(
      null,
      "",
      "/auth/callback?code=synthetic&state=synthetic",
    );
    const auth = new FakeAuthService("unauthenticated");
    auth.callbackReturn = "/recommendations";
    render(<App authService={auth} config={publicConfig} />);
    expect(
      await screen.findByRole("heading", { name: "Decision review queue" }),
    ).toBeVisible();
  });

  it("fails a callback safely without rendering provider details", async () => {
    window.history.replaceState(
      null,
      "",
      "/auth/callback?error=synthetic-private-error",
    );
    const auth = new FakeAuthService("unauthenticated");
    auth.callbackError = true;
    render(<App authService={auth} config={publicConfig} />);
    expect(
      await screen.findByRole("heading", { name: "Sign-in could not be completed" }),
    ).toBeVisible();
    expect(screen.queryByText(/synthetic-private-error/i)).not.toBeInTheDocument();
  });

  it("redirects an already authenticated user away from login", async () => {
    window.history.replaceState(null, "", "/login");
    render(
      <App authService={new FakeAuthService("authenticated")} config={publicConfig} />,
    );
    expect(
      await screen.findByRole("heading", {
        name: "Know what needs attention—and why.",
      }),
    ).toBeVisible();
  });

  it("provides forbidden, unavailable, unknown-route, and logout foundations", async () => {
    const auth = new FakeAuthService("authenticated");
    const user = userEvent.setup();

    window.history.replaceState(null, "", "/forbidden");
    const view = render(<App authService={auth} config={publicConfig} />);
    expect(
      await screen.findByRole("heading", { name: "Permission required" }),
    ).toBeVisible();

    window.history.pushState(null, "", "/unavailable");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(
      await screen.findByRole("heading", {
        name: "OpsMind is temporarily unavailable",
      }),
    ).toBeVisible();

    window.history.pushState(null, "", "/not-a-real-route");
    window.dispatchEvent(new PopStateEvent("popstate"));
    expect(
      await screen.findByRole("heading", { name: "There is no page at this address" }),
    ).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() => {
      expect(auth.logoutCalls).toBe(1);
    });
    view.unmount();
  });
});
