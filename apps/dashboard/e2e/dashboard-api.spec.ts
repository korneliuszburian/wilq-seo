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
      page.getByText("WILQ pokazuje tylko metryki z API/evidence.").first()
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dzisiejszy panel operatora" })).toBeVisible();
    await expect(page.getByText("Merchant: feed/product issues do przeglądu")).toBeVisible();
    await expect(page.getByText("Content: GSC query/page + WordPress inventory")).toBeVisible();
    await expect(page.getByText("GA4: landing/source/campaign quality review")).toBeVisible();
    await expect(page.getByText("Ads: blocker OAuth przed analizą spendu")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Priorytety dnia" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Budżet i ryzyko wydatków" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kandydaci działań API" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Realne metric facts zapisane lokalnie" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejka taktyczna WILQ" })).toBeVisible();
    await expect(page.getByText(/Wymiar:/).first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Google Ads connector ready for first search-term refresh" }).first()
    ).toBeVisible();

    await expect
      .poll(() => apiResponses.includes("200 /api/dashboard/command-center"))
      .toBe(true);
    expect(apiResponses.every((entry) => entry.startsWith("200 "))).toBe(true);
  });

  test("ads doctor route exposes dedicated OAuth diagnostics", async ({ page }) => {
    await page.goto("/ads-doctor");

    await expect(page.getByRole("heading", { name: "Ads Doctor" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status Google Ads" })).toBeVisible();
    await expect(page.getByText("Google Ads: OAuth blokuje live metryki")).toBeVisible();
    await expect(page.getByText(/oauth_error=/).first()).toBeVisible();
    await expect(page.getByText("Campaign overview")).toBeVisible();
    await expect(page.getByRole("link", { name: "act_configure_google_ads_env" }).first()).toBeVisible();
  });

  test("ga4 route exposes metric-backed workflow focus", async ({ page }) => {
    await page.goto("/ga4");

    await expect(page.getByRole("heading", { name: "GA4", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status GA4 / Landing Quality" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "GA4: landing/source/campaign behavior" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "GA4: tracking/conversion readiness" })).toBeVisible();
    await expect(page.getByText(/active_users:/).first()).toBeVisible();
    await expect(page.getByText(/landing_page=/).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "act_review_ga4_tracking_quality" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Analytics Safety Gate" })).toBeVisible();
  });

  test("seo and content routes expose dedicated Content Diagnostics", async ({ page }) => {
    await page.goto("/seo-gsc");

    await expect(page.getByRole("heading", { name: "SEO / GSC" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status SEO / Content" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "GSC: query/page matrix" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "WordPress: inventory protection" })).toBeVisible();
    await expect(page.getByText(/GSC: .*->/).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "act_prepare_content_refresh_queue" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Content Safety Gate" })).toBeVisible();

    await page.goto("/content-planner");

    await expect(page.getByRole("heading", { name: "Content Planner", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status SEO / Content" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "ActionObject focus" })).toBeVisible();
  });

  test("action detail route shows validation, evidence and payload preview", async ({ page }) => {
    await page.goto("/actions/act_configure_google_ads_env");

    await expect(
      page.getByRole("heading", { name: "Odnow Google Ads OAuth refresh token" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence And Diagnosis" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Payload Preview" })).toBeVisible();
    await expect(page.getByText("Evidence: ev_connector_google_ads_status")).toBeVisible();
    await expect(page.getByText("Jawne potwierdzenie apply")).toBeVisible();
    await page.getByRole("button", { name: "Potwierdź apply" }).click();
    await expect(page.getByText("Apply: blocked")).toBeVisible();
    await expect(
      page.getByText(/Błędy apply: .*Action mode must be apply before external execution/)
    ).toBeVisible();
    await expect(page.getByText("Audit event: apply_blocked")).toBeVisible();
  });

  test("merchant route renders live Merchant Diagnostics evidence links", async ({ page }) => {
    await page.goto("/merchant");

    await expect(page.getByRole("heading", { name: "Merchant Center", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status Merchant Center" })).toBeVisible();
    await expect(page.getByText("Merchant Center: feed/product health")).toBeVisible();
    await expect(page.getByText("Merchant Center: kolejka feed/product issues")).toBeVisible();
    await expect(page.getByText(/Merchant: .*availability_updated/).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "ActionObject focus" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Przygotuj kolejkę przeglądu feedu Merchant Center" }).first()
    ).toBeVisible();
    await expect(page.getByText(/Apply zablokowany/)).toBeVisible();
    await expect(page.getByText(/"action_type": "merchant_feed_issue"/)).toBeVisible();
    await page.getByRole("button", { name: "Waliduj" }).first().click();
    await expect(page.getByText("Wynik:")).toBeVisible();
    await expect(page.getByText("valid").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Feed Safety Gate" })).toBeVisible();

    const evidenceLink = page.getByRole("link", { name: /ev_refresh_refresh_google_merchant_center/ }).first();
    await expect(evidenceLink).toBeVisible();
    await evidenceLink.click();
    await expect(
      page.getByRole("heading", { name: /ev_refresh_refresh_google_merchant_center/ })
    ).toBeVisible();
    await expect(page.getByText("Source connector: google_merchant_center")).toBeVisible();
  });

  test("localo route exposes OAuth blocker without invented local metrics", async ({ page }) => {
    await page.goto("/localo");

    await expect(page.getByRole("heading", { name: "Localo", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Local Visibility Focus" })).toBeVisible();
    await expect(page.getByText(/LOCALO_ACCESS_TOKEN/).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "ev_connector_localo_status" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Local Visibility Safety Gate" })).toBeVisible();
    await expect(page.getByText(/Brak LOCALO_ACCESS_TOKEN jest blockerem/)).toBeVisible();
    await expect(page.getByText(/local ranking/i)).toHaveCount(0);
    await expect(page.getByText(/pozycja lokalna/i)).toHaveCount(0);
  });
});
