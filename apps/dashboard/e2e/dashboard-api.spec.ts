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
    await expect(page.getByRole("heading", { name: "Realne metric facts zapisane lokalnie" })).toBeVisible();
    await expect(page.getByText(/Wymiar:/).first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Google Ads connector ready for first search-term refresh" }).first()
    ).toBeVisible();

    await expect
      .poll(() => apiResponses.includes("200 /api/dashboard/command-center"))
      .toBe(true);
    expect(apiResponses.every((entry) => entry.startsWith("200 "))).toBe(true);
  });

  test("ads doctor route exposes OAuth action focus from MarketingBrief", async ({ page }) => {
    await page.goto("/ads-doctor");

    await expect(page.getByRole("heading", { name: "Ads Doctor" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Ads Focus" })).toBeVisible();
    await expect(page.getByText("Google Ads: najpierw napraw OAuth, potem diagnozuj spend")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Spend Safety Gate" })).toBeVisible();
    await expect(page.getByRole("link", { name: "act_configure_google_ads_env" }).first()).toBeVisible();
  });

  test("ga4 and gsc routes expose metric-backed workflow focus", async ({ page }) => {
    await page.goto("/ga4");

    await expect(page.getByRole("heading", { name: "GA4", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "GA4 Quality Focus" })).toBeVisible();
    await expect(page.getByText(/active_users:/).first()).toBeVisible();
    await expect(page.getByText(/landing_page=/).first()).toBeVisible();
    await expect(page.getByText(/odświeżone/).first()).toBeVisible();

    await page.goto("/seo-gsc");

    await expect(page.getByRole("heading", { name: "SEO / GSC" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Search Console Content Focus" })).toBeVisible();
    await expect(page.getByText("GSC: przełóż widoczność na kolejkę treści")).toBeVisible();
  });

  test("action detail route shows validation, evidence and payload preview", async ({ page }) => {
    await page.goto("/actions/act_configure_google_ads_env");

    await expect(
      page.getByRole("heading", { name: "Odnow Google Ads OAuth refresh token" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence And Diagnosis" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Payload Preview" })).toBeVisible();
    await expect(page.getByText("Evidence: ev_connector_google_ads_status")).toBeVisible();
  });

  test("merchant route renders live MarketingBrief evidence links", async ({ page }) => {
    await page.goto("/merchant");

    await expect(page.getByRole("heading", { name: "Merchant Center", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Feed/Product Focus" })).toBeVisible();
    await expect(
      page.getByText("Merchant Center: zacznij od feed/product issues")
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "ActionObject focus" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Przygotuj kolejkę przeglądu feedu Merchant Center" }).first()
    ).toBeVisible();
    await expect(page.getByText(/Apply zablokowany/)).toBeVisible();
    await expect(page.getByText(/"action_type": "merchant_feed_issue"/)).toBeVisible();
    await page.getByRole("button", { name: "Waliduj" }).first().click();
    await expect(page.getByText("Wynik:")).toBeVisible();
    await expect(page.getByText("valid").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Safety Gate" })).toBeVisible();

    const evidenceLink = page.getByRole("link", { name: /ev_refresh_refresh_google_merchant_center/ }).first();
    await expect(evidenceLink).toBeVisible();
    await evidenceLink.click();
    await expect(
      page.getByRole("heading", { name: /ev_refresh_refresh_google_merchant_center/ })
    ).toBeVisible();
    await expect(page.getByText("Source connector: google_merchant_center")).toBeVisible();
  });
});
