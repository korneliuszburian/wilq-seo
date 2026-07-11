import { expect, test } from "@playwright/test";

test.describe("WILQ Ads summary current behavior", () => {
  test("renders a current evidence-first decision without raw internals", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto("/ads-doctor");

    await expect(page.getByRole("heading", { name: "Reklamy i pomiar", exact: true })).toBeVisible({
      timeout: 30_000
    });
    await expect(page.getByText("Najpierw pomiar", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejka diagnostyczna" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Bezpieczne tryby pracy" })).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "ROAS, przychód, waste i konwersje są zablokowane do czasu potwierdzenia danych."
      })
    ).toBeVisible();
    await expect(page.getByText(/ev_refresh_/)).toHaveCount(0);
    await expect(page.getByText(/act_/)).toHaveCount(0);
    await expect(page.getByText("ActionObjecty")).toHaveCount(0);
    await expect(page.getByText("Ads Doctor")).toHaveCount(0);
  });
});
