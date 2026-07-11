import { expect, test } from "@playwright/test";

test.describe("WILQ Knowledge current behavior", () => {
  test("renders the knowledge decision before deferred catalogs", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto("/knowledge");

    await expect(page.getByRole("heading", { name: "Wiedza", exact: true })).toBeVisible({
      timeout: 30_000
    });
    await expect(page.getByRole("heading", { name: "Najbliższa wiedza do sprawdzenia" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co blokuje produkcję treści" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejka sprawdzania wiedzy" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pokaż kartę" })).toBeVisible();

    await page.getByRole("button", { name: "Pokaż kartę" }).click();
    await expect(page.getByRole("heading", { name: "Karty wiedzy" })).toBeVisible();
    await page.getByRole("button", { name: "Zobacz pełne zasady pracy" }).first().click();
    await expect(page.getByRole("heading", { name: "Zasady pracy" })).toBeVisible();
    await expect(page.getByText(/Evidence Registry|Knowledge Cards|Machine-Readable Playbooks/)).toHaveCount(0);
  });
});
