import { expect, test } from "@playwright/test";

test.describe("WILQ dashboard API-backed smoke", () => {
  test("command center renders live API-backed sections", async ({ page }) => {
    const apiResponses: string[] = [];
    page.on("response", (response) => {
      const url = new URL(response.url());
      if (url.pathname.startsWith("/api/")) {
        apiResponses.push(`${response.status()} ${url.pathname}`);
      }
    });

    await page.goto("/command-center");

    await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
    await expect(
      page.getByText("No WILQ API evidence means no marketing recommendation.")
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Priorytety dnia" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Budżet i ryzyko wydatków" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kandydaci działań API" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Google Ads connector ready for first search-term refresh" }).first()
    ).toBeVisible();

    await expect
      .poll(() => apiResponses.includes("200 /api/dashboard/command-center"))
      .toBe(true);
    expect(apiResponses.every((entry) => entry.startsWith("200 "))).toBe(true);
  });

  test("operating routes expose evidence, actions and missing credentials", async ({ page }) => {
    await page.goto("/ads-doctor");

    await expect(page.getByRole("heading", { name: "Ads Doctor" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence Registry" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Connector Refresh Runs" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Actions" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Connector Status" })).toBeVisible();
    await expect(page.getByText("Missing credentials").first()).toBeVisible();
  });

  test("action detail route shows validation, evidence and payload preview", async ({ page }) => {
    await page.goto("/actions/act_configure_google_ads_env");

    await expect(
      page.getByRole("heading", { name: "Configure Google Ads local .env" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence And Diagnosis" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Payload Preview" })).toBeVisible();
    await expect(page.getByText("Evidence: ev_connector_google_ads_status")).toBeVisible();
  });
});
