import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormField } from "./FormField";

describe("FormField", () => {
  it("connects labels, help, and accessible error state", () => {
    const { rerender } = render(
      <FormField
        help="Use the public product identifier."
        id="product"
        label="Product"
      />,
    );
    expect(screen.getByLabelText("Product")).toHaveAccessibleDescription(
      "Use the public product identifier.",
    );
    rerender(<FormField error="Product is required." id="product" label="Product" />);
    expect(screen.getByLabelText("Product")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("textbox")).toHaveAccessibleDescription(
      "Product is required.",
    );
  });
});
