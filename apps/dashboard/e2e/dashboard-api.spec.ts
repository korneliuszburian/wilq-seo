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

    const commandCenterResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/dashboard/command-center" && response.status() === 200;
    });
    await page.goto("/command-center");
    await commandCenterResponse;

    await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
    await expect(
      page.getByText("WILQ pokazuje tylko metryki z API/evidence.").first()
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dzisiejsze decyzje marketera" })).toBeVisible();
    await expect(page.getByText("produkty").first()).toBeVisible();
    await expect(page.getByText("10900").first()).toBeVisible();
    await expect(page.getByText("landing groups").first()).toBeVisible();
    await expect(page.getByText("10").first()).toBeVisible();
    await expect(page.getByText("kampanie").first()).toBeVisible();
    await expect(page.getByText("18").first()).toBeVisible();
    await expect(page.getByText("search terms").first()).toBeVisible();
    await expect(page.getByText("50").first()).toBeVisible();
    await expect(page.getByText("Merchant: feed/product issues do przeglądu")).toHaveCount(0);
    await expect(page.getByText("Content: GSC query/page + WordPress inventory")).toHaveCount(0);
    await expect(page.getByText("GA4: landing/source/campaign quality review")).toHaveCount(0);
    await expect(page.getByText("Ads: live campaign metrics dostępne")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Źródła i ograniczenia" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Realne metric facts zapisane lokalnie" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Dzisiejsze konkretne taktyki" })).toHaveCount(0);
    await expect(page.getByText("Jak Codex może pomóc").first()).toBeVisible();
    await expect(page.getByText("Prompt do Codex").first()).toBeVisible();
    await expect(page.getByText("Context-pack: /api/codex/context-pack").first()).toBeVisible();
    await expect(page.getByText(/Oczekiwany wynik:/).first()).toBeVisible();
    await expect(page.getByText(/Wymiar:/)).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Ułóż kolejkę refresh/merge/create dla treści SEO" })
    ).toBeVisible();
    await expect(page.getByText("Skill: wilq-content-strategist")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Priorytety dnia" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Budżet i ryzyko wydatków" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Kandydaci działań API" })).toHaveCount(0);
    await expect(page.getByText("connector_configured")).toHaveCount(0);
    await expect(page.getByText("No performance metrics have been collected")).toHaveCount(0);
    await expect(page.getByText("Run a read-only")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Demo dla marketera" })).toHaveCount(0);
    await expect(page.getByText(/priority \d+/i)).toHaveCount(0);
    await expect(page.getByText("GA4: (not set) / (not set)")).toHaveCount(0);

    await expect
      .poll(() => apiResponses.includes("200 /api/dashboard/command-center"))
      .toBe(true);
    expect(apiResponses.every((entry) => entry.startsWith("200 "))).toBe(true);
  });

  test("ads doctor route exposes live metric-backed diagnostics", async ({ page }) => {
    await page.goto("/ads-doctor");

    await expect(page.getByRole("heading", { name: "Ads Doctor" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status Google Ads" })).toBeVisible();
    await expect(page.getByText("Google Ads: live data dostępne")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Google Ads: campaign activity rows" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Google Ads: search terms read-only rows" })
    ).toBeVisible();
    await expect(page.getByText("Brakujące read contracts:").first()).toBeVisible();
    await expect(page.getByText(/clicks:/).first()).toBeVisible();
    await expect(page.getByText("Konwersje").first()).toBeVisible();
    await expect(page.getByText("Wartość konw.").first()).toBeVisible();
    await expect(page.getByText("Google Ads: live read gotowy do kolejnego kroku")).toBeVisible();
    await expect(page.getByText("Google Ads connector ma live metric facts.")).toBeVisible();
    await expect(page.getByRole("link", { name: "ev_connector_google_ads_status" }).first()).toBeVisible();
  });

  test("ga4 route exposes metric-backed workflow focus", async ({ page }) => {
    await page.goto("/ga4");

    await expect(page.getByRole("heading", { name: "GA4", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status GA4 / Landing Quality" })).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /GA4: (landing\/source\/campaign behavior|brak landing\/source\/campaign breakdown)/
      })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "GA4: tracking/conversion readiness" })).toBeVisible();
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
    await page.goto("/actions/act_review_merchant_feed_issues");

    await expect(
      page.getByRole("heading", { name: "Przygotuj kolejkę przeglądu feedu Merchant Center" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Evidence And Diagnosis" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Payload Preview" })).toBeVisible();
    await expect(page.getByText(/Evidence: .*ev_refresh_refresh_google_merchant_center/)).toBeVisible();
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
    await expect(page.getByText("Zgłoszenia", { exact: true })).toBeVisible();
    await expect(page.getByText("Affected", { exact: true })).toHaveCount(0);
    await expect(page.getByText(/zgłoszenia:/).first()).toBeVisible();
    await expect(page.getByText(/kontekst:/).first()).toBeVisible();
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

  test("localo route exposes access readiness without invented local metrics", async ({ page }) => {
    await page.goto("/localo");

    await expect(page.getByRole("heading", { name: "Localo", exact: true })).toBeVisible();
    await expect(page.getByText(/Brak konkretnych Localo ranking\/GBP facts/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Local Visibility Safety Gate" })).toBeVisible();
    await expect(page.getByText(/MCP initialize=200 potwierdza access/)).toBeVisible();
    await expect(page.getByText(/LOCALO_ACCESS_TOKEN/)).toHaveCount(0);
    await expect(page.getByText(/local ranking/i)).toHaveCount(0);
    await expect(page.getByText(/pozycja lokalna/i)).toHaveCount(0);
  });
});
