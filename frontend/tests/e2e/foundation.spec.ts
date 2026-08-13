import { expect, test } from "@playwright/test";

test("presents the public login foundation without a password form", async ({
  page,
}) => {
  await page.goto("/login");
  await expect(
    page.getByRole("heading", {
      name: /decisions backed by visible operational evidence/i,
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /continue with zitadel/i }),
  ).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
});

test("protects deep links and preserves a bounded return path", async ({ page }) => {
  await page.goto("/products/product-123?section=demand");
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("button", { name: /continue with zitadel/i }),
  ).toBeVisible();
});
