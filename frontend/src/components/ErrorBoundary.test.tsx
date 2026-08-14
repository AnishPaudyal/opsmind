import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ErrorBoundary } from "./ErrorBoundary";

function BrokenComponent(): never {
  throw new Error("synthetic private render detail");
}

describe("ErrorBoundary", () => {
  it("renders a bounded fallback without exposing the thrown detail", () => {
    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>,
    );
    expect(
      screen.getByRole("heading", { name: "The workspace could not render" }),
    ).toBeVisible();
    expect(
      screen.queryByText(/synthetic private render detail/i),
    ).not.toBeInTheDocument();
  });
});
