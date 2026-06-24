import { expect, type Page, test } from "@playwright/test";

const routeReadyTimeoutMs = 30_000;

async function expectApiBackedRouteHeading(
  page: Page,
  name: string,
  options: { exact?: boolean } = {}
) {
  await expect(page.getByText("Ładowanie stanu WILQ API")).toBeHidden({
    timeout: routeReadyTimeoutMs
  });
  await expect(page.getByRole("heading", { name, exact: options.exact })).toBeVisible({
    timeout: routeReadyTimeoutMs
  });
}

test.describe("WILQ dashboard API-backed smoke", () => {
  test("command center renders live API-backed sections", async ({ page }) => {
    test.setTimeout(60_000);

    const apiResponses: string[] = [];
    page.on("response", (response) => {
      const url = new URL(response.url());
      if (url.pathname.startsWith("/api/")) {
        apiResponses.push(`${response.status()} ${url.pathname}`);
      }
    });

    const commandCenterResponse = page.waitForResponse(
      (response) => {
        const url = new URL(response.url());
        return url.pathname === "/api/dashboard/command-center" && response.status() === 200;
      },
      { timeout: 60_000 }
    );
    await page.goto("/command-center");
    await commandCenterResponse;

    await expect(page.getByRole("heading", { name: "Command Center" })).toBeVisible();
    await expect(
      page.getByText("WILQ pokazuje tylko metryki z API/evidence.").first()
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dzisiejsze decyzje marketera" })).toBeVisible();
    await expect(page.getByText("Decyzje").first()).toBeVisible();
    await expect(page.getByText("Blockery").first()).toBeVisible();
    await expect(page.getByText("Świeżość źródeł").first()).toBeVisible();
    await expect(page.getByText("Dowody w API").first()).toBeVisible();
    await expect(page.getByText(/potwierdzonych śladów w WILQ API/).first()).toBeVisible();
    await expect(page.getByText("Akcje do walidacji").first()).toBeVisible();
    await expect(page.getByText(/bezpieczna akcja do walidacji/).first()).toBeVisible();
    await expect(page.getByText("Przykładowe dowody")).toHaveCount(0);
    await expect(page.getByText(/ev_refresh_/)).toHaveCount(0);
    await expect(page.getByText(/act_review_merchant_feed_issues/)).toHaveCount(0);
    await expect(page.getByText(/^Evidence:/)).toHaveCount(0);
    await expect(page.getByText("Przykładowe evidence")).toHaveCount(0);
    await expect(page.getByText("ponowne zatwierdzenie produktu").first()).toBeVisible();
    await expect(page.getByText("jakość leadów").first()).toBeVisible();
    await expect(page.getByText("opłacalność").first()).toBeVisible();
    await expect(page.getByText("zmarnowany budżet").first()).toBeVisible();
    await expect(page.getByText("approval restored")).toHaveCount(0);
    await expect(page.getByText("lead uplift")).toHaveCount(0);
    await expect(page.getByText("traffic uplift")).toHaveCount(0);
    await expect(page.getByText("authority improvement")).toHaveCount(0);
    await expect(page.getByText("off-topic content recommendation")).toHaveCount(0);
    await expect(page.getByText("funnel diagnosis")).toHaveCount(0);
    await expect(page.getByText("attribution verdict")).toHaveCount(0);
    await expect(page.getByText("GA4 write")).toHaveCount(0);
    await expect(page.getByText("competitor visibility")).toHaveCount(0);
    await expect(page.getByText("search-term waste")).toHaveCount(0);
    await expect(page.getByText("profitability")).toHaveCount(0);
    await expect(page.getByText("wasted budget")).toHaveCount(0);
    await expect(page.getByText("Merchant: feed/product issues do przeglądu")).toHaveCount(0);
    await expect(page.getByText("Content: GSC query/page + WordPress inventory")).toHaveCount(0);
    await expect(page.getByText("GA4: landing/source/campaign quality review")).toHaveCount(0);
    await expect(page.getByText("Ads: live campaign metrics dostępne")).toHaveCount(0);
    await expect(page.getByText("Czego nie twierdzimy").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Źródła i ograniczenia" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Realne metric facts zapisane lokalnie" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Dzisiejsze konkretne taktyki" })).toHaveCount(0);
    await expect(page.getByText(/Codex:/).first()).toBeVisible();
    await expect(page.getByText("Context-pack: /api/codex/context-pack")).toHaveCount(0);
    await expect(page.getByText(/Wymiar:/)).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Ułóż kolejkę odświeżenia i scalania treści SEO" })
    ).toBeVisible();
    await expect(page.getByText("Codex: strategia treści")).toBeVisible();
    await expect(page.getByText("Skill: wilq-content-strategist")).toHaveCount(0);
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

    await expectApiBackedRouteHeading(page, "Ads Doctor");
    await expect(page.getByRole("heading", { name: "Status Google Ads" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).toBeVisible();
    await expect(page.getByText("Przejrzyj aktywność kampanii Google Ads")).toBeVisible();
    await expect(page.getByText("Operator Ads")).toBeVisible();
    await expect(page.getByText("Budżety").first()).toBeVisible();
    await expect(page.getByText("Rekom.").first()).toBeVisible();
    await expect(page.getByText("Zablokowane wnioski i wdrożenia")).toBeVisible();
    await expect(page.getByText("ActionObjecty").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Ads" })).toBeVisible();
    await expect(page.getByText("Brakujące kontrakty:").first()).toBeVisible();
    await expect(page.getByText("Konwersje").first()).toBeVisible();
    await expect(page.getByText("Wartość konw.").first()).toBeVisible();
    await expect(page.getByRole("link", { name: "ev_connector_google_ads_status" }).first()).toBeVisible();
    await expect(page.getByText("Handoff blockera Ads")).toHaveCount(0);
    await expect(page.getByText(/handoff blockera OAuth/i)).toHaveCount(0);
    await expect(page.getByText("Read contract Ads")).toHaveCount(0);
    await expect(page.getByText("Search terms read-only")).toHaveCount(0);
    await expect(page.getByText("Campaign activity read contract")).toHaveCount(0);
    await expect(page.getByText("Evidence", { exact: true })).toHaveCount(0);
    await expect(page.getByText("configured", { exact: true })).toHaveCount(0);
  });

  test("custom segments route exposes review-only segment candidates", async ({ page }) => {
    await page.goto("/ads-doctor/custom-segments");

    await expectApiBackedRouteHeading(page, "Custom Segments", { exact: true });
    await expect(page.getByRole("heading", { name: "Co marketer może przygotować teraz" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia segmentów" })).toBeVisible();
    await expect(page.getByText(/Search terms:|Brak search-term rows/).first()).toBeVisible();
    await expect(page.getByText(/nie twierdzi, że segment ma zasięg|audience size/i).first()).toBeVisible();
    await expect(page.getByText("Evidence Registry")).toHaveCount(0);
    await expect(page.getByText("Connector Refresh Runs")).toHaveCount(0);
  });

  test("demand gen route exposes readiness blocker instead of generic registry", async ({ page }) => {
    await page.goto("/ads-doctor/demand-gen");

    await expectApiBackedRouteHeading(page, "Demand Gen", { exact: true });
    await expect(page.getByRole("heading", { name: "Demand Gen: brak kampanii do rekomendacji" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma wiedzieć przed planem Demand Gen" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Demand Gen" })).toBeVisible();
    await expect(page.getByText("kampanie Ads")).toBeVisible();
    await expect(page.getByText("Brakujące kontrakty").first()).toBeVisible();
    await expect(page.getByText("Review-only ActionObject", { exact: true })).toBeVisible();
    await expect(page.getByText("Podgląd walidacji gotowości Demand Gen")).toBeVisible();
    await expect(page.getByText("rekomendacja launchu Demand Gen").first()).toBeVisible();
    await expect(page.getByText("API-backed operating surface")).toHaveCount(0);
    await expect(page.getByText("Evidence Registry")).toHaveCount(0);
    await expect(page.getByText("Connector Refresh Runs")).toHaveCount(0);
  });

  test("ga4 route exposes metric-backed workflow focus", async ({ page }) => {
    await page.goto("/ga4");

    await expectApiBackedRouteHeading(page, "GA4", { exact: true });
    await expect(page.getByRole("heading", { name: "Status GA4 / pomiar i jakość ruchu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia GA4" })).toBeVisible();
    await expect(page.getByRole("link", { name: "act_review_ga4_tracking_quality" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa GA4" })).toBeVisible();
    await expect(page.getByText("GA4: landing/source/campaign behavior")).toHaveCount(0);
    await expect(page.getByText("GA4: tracking/conversion readiness")).toHaveCount(0);
    await expect(page.getByText("Analytics Safety Gate")).toHaveCount(0);
  });

  test("seo and content routes expose dedicated Content Diagnostics", async ({ page }) => {
    await page.goto("/seo-gsc");

    await expectApiBackedRouteHeading(page, "SEO / GSC");
    await expect(page.getByRole("heading", { name: "Status SEO / Content" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma zrobić teraz z treściami" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Bezpieczny tryb treści" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Content" })).toBeVisible();
    await expect(page.getByText("GSC: query/page matrix")).toHaveCount(0);
    await expect(page.getByText("WordPress: inventory protection")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "act_prepare_content_refresh_queue" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa treści" })).toBeVisible();

    await page.goto("/content-planner");

    await expectApiBackedRouteHeading(page, "Content Planner", { exact: true });
    await expect(page.getByRole("heading", { name: "Status SEO / Content" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "ActionObjecty do walidacji" })).toBeVisible();
  });

  test("action detail route shows validation, evidence and payload preview", async ({ page }) => {
    await page.goto("/actions/act_review_merchant_feed_issues");

    await expectApiBackedRouteHeading(page, "Przygotuj kolejkę przeglądu feedu Merchant Center");
    await expect(page.getByRole("heading", { name: "Dowody i diagnoza" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Podgląd payloadu" })).toBeVisible();
    await expect(page.getByText(/Dowody: .*ev_refresh_refresh_google_merchant_center/)).toBeVisible();
    await expect(page.getByText(/^Evidence:/)).toHaveCount(0);
    await expect(page.getByText("Dry-run preview", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Generuj preview" }).click();
    await expect(page.getByText("Audit event: action_preview_generated")).toBeVisible();
    await expect(page.getByText("Jawne potwierdzenie preview")).toBeVisible();
    await page.getByRole("button", { name: "Potwierdź preview" }).click();
    await expect(page.getByText("Potwierdzenie: confirmed")).toBeVisible();
    await expect(page.getByText("Audit event: action_apply_confirmed")).toBeVisible();
    await expect(page.getByText(/Apply nadal: zablokowany/)).toHaveCount(1);
    await expect(page.getByText("Impact sanity check", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Sprawdź impact" }).click();
    await expect(page.getByText("Impact check: checked")).toBeVisible();
    await expect(page.getByText("Audit event: action_impact_check_completed")).toBeVisible();
    await expect(page.getByText(/Apply nadal: zablokowany/)).toHaveCount(2);
  });

  test("actions route starts with ActionObjects instead of registry dumps", async ({ page }) => {
    await page.goto("/actions");

    await expectApiBackedRouteHeading(page, "ActionObjecty", { exact: true });
    await expect(page.getByRole("heading", { name: "ActionObjecty do przeglądu" })).toBeVisible();
    await expect(page.getByText("Do walidacji", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Odnow Google Ads OAuth refresh token")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "OPPORTUNITIES" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Connector Refresh Runs" })).toHaveCount(0);
  });

  test("workflows route exposes decision-backed operator workflows", async ({ page }) => {
    await page.goto("/workflows");

    await expectApiBackedRouteHeading(page, "Workflowy WILQ");
    await expect(page.getByRole("heading", { name: "Workflowy decyzyjne" })).toBeVisible();
    await expect(page.getByText("Plan dnia WILQ")).toBeVisible();
    await expect(page.getByText("Merchant feed review")).toBeVisible();
    await expect(page.getByText("GSC content doctor")).toBeVisible();
    await expect(page.getByText("Ads daily check")).toBeVisible();
    await expect(page.getByText("Localo visibility review")).toBeVisible();
    await expect(page.getByText("decyzje").first()).toBeVisible();
    await expect(page.getByText("blockery").first()).toBeVisible();
    await expect(page.getByText("podgląd budżetu").first()).toBeVisible();
    await expect(page.getByText("wilq-daily-command")).toHaveCount(0);
    await expect(page.getByText("Workflow definition runs against WILQ API")).toHaveCount(0);
    await expect(page.getByText("Fetch WILQ API context")).toHaveCount(0);
    await expect(page.getByText("Rejestr workflowów")).toHaveCount(0);
  });

  test("knowledge route maps source knowledge to decisions", async ({ page }) => {
    await page.goto("/knowledge");

    await expectApiBackedRouteHeading(page, "Baza wiedzy WILQ");
    await expect(page.getByRole("heading", { name: "Mapa wiedzy do decyzji" })).toBeVisible();
    await expect(page.getByText("Powiązania")).toBeVisible();
    await expect(page.getByText("Karty wiedzy").first()).toBeVisible();
    await expect(page.getByText("Playbooki").first()).toBeVisible();
    await expect(page.getByText("Reguły").first()).toBeVisible();
    await expect(page.getByText("Ads daily check")).toBeVisible();
    await expect(page.getByText("Merchant feed review")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Karty źródłowe" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Playbooki maszynowe" })).toBeVisible();
    await expect(page.getByText("Knowledge Cards")).toHaveCount(0);
    await expect(page.getByText("Machine-Readable Playbooks")).toHaveCount(0);
  });

  test("merchant route renders live Merchant Diagnostics evidence links", async ({ page }) => {
    await page.goto("/merchant");

    await expectApiBackedRouteHeading(page, "Merchant Center", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Merchant Center" })).toBeVisible();
    await expect(page.getByText("Dowody i ograniczenia Merchant")).toBeVisible();
    await expect(page.getByText("Merchant Center: feed/product health")).toHaveCount(0);
    await expect(page.getByText("Merchant Center: kolejka feed/product issues")).toHaveCount(0);
    await expect(page.getByText("Zgłoszenia", { exact: true })).toBeVisible();
    await expect(page.getByText("Affected", { exact: true })).toHaveCount(0);
    await expect(page.getByText("configured", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Evidence", { exact: true })).toHaveCount(0);
    await expect(page.getByText("dostęp skonfigurowany")).toBeVisible();
    await expect(page.getByText("metryki feedu dostępne")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Gotowość próbek produktów" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Wpływ ceny produktu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "ActionObjecty do walidacji" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Przygotuj kolejkę przeglądu feedu Merchant Center" }).first()
    ).toBeVisible();
    await expect(page.getByText(/Apply zablokowany/)).toBeVisible();
    await page.getByRole("button", { name: "Waliduj" }).first().click();
    await expect(page.getByText("Wynik:")).toBeVisible();
    await expect(page.getByText("valid").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa feedu" })).toBeVisible();

    const evidenceLink = page.getByRole("link", { name: /ev_refresh_refresh_google_merchant_center/ }).first();
    await expect(evidenceLink).toBeVisible();
    await evidenceLink.click();
    await expect(
      page.getByRole("heading", { name: /ev_refresh_refresh_google_merchant_center/ })
    ).toBeVisible();
    await expect(page.getByText("Źródło: google_merchant_center")).toBeVisible();
  });

  test("localo route exposes aggregate facts without unsupported local claims", async ({ page }) => {
    await page.goto("/localo");

    await expectApiBackedRouteHeading(page, "Localo", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Localo / widoczność lokalna" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma wiedzieć o Localo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Localo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa Localo/GBP" })).toBeVisible();
    await expect(
      page.getByText(/Przejrzyj agregaty widoczności lokalnej z Localo/)
    ).toBeVisible();
    await expect(page.getByText(/lista lokalizacji/)).toBeVisible();
    await expect(page.getByText(/rankingi lokalne/)).toBeVisible();
    await expect(page.getByText(/opinie/)).toBeVisible();
    await expect(page.getByText(/widoczność konkurencji/).first()).toBeVisible();
    await expect(page.getByText(/MCP initialize zwrócił 200/)).toBeVisible();
    await expect(page.getByText(/LOCALO_ACCESS_TOKEN/)).toHaveCount(0);
    await expect(page.getByText(/Dokończ Localo access/)).toHaveCount(0);
    await expect(page.getByText(/Local Visibility Focus/)).toHaveCount(0);
    await expect(page.getByText("Taktyki z WILQ API")).toHaveCount(0);
    await expect(page.getByText("Metric facts")).toHaveCount(0);
    await expect(page.getByText("24 Taktyki")).toHaveCount(0);
  });

  test("ahrefs route exposes authority context and gap safety state", async ({ page }) => {
    await page.goto("/ahrefs");

    await expectApiBackedRouteHeading(page, "Ahrefs", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Ahrefs / dowody SEO" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma wiedzieć o Ahrefs" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Ahrefs" })).toBeVisible();
    await expect(page.getByText(/odczyt autorytetu Ahrefs|metryki Ahrefs dostępne/).first()).toBeVisible();
    await expect(page.getByText(/Przejrzyj rekordy luk Ahrefs|Brak typed gap records/).first()).toBeVisible();
    await expect(page.getByText(/DR|brak facts/).first()).toBeVisible();
    await expect(page.getByText("Gap records").first()).toBeVisible();
    await expect(page.getByText(/gotowe|zablokowane/).first()).toBeVisible();
    await expect(page.getByText(/competitor_page|strony konkurencji/).first()).toBeVisible();
    await expect(page.getByText(/Strona konkurencji:|rekordy luk treści/).first()).toBeVisible();
    await expect(page.getByText(/poprawa autorytetu/).first()).toBeVisible();
    await expect(page.getByText("Evidence Registry")).toHaveCount(0);
    await expect(page.getByText("Connector Refresh Runs")).toHaveCount(0);
    await expect(page.getByText("API-backed operating surface")).toHaveCount(0);
  });
});
