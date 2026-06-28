import { expect, type Page, test } from "@playwright/test";

const routeReadyTimeoutMs = 30_000;
const forbiddenVisibleCopy = [
  "ActionObjecty",
  "Ads Doctor",
  "API-backed operating surface",
  "Command Center",
  "Connector Refresh Runs",
  "Content Planner",
  "Evidence Registry",
  "Kandydaci działań API",
  "audience size",
  "brak facts",
  "competitor_page",
  "mapping-review",
  "migration-map",
  "payload",
  "target_site"
];

async function expectApiBackedRouteHeading(
  page: Page,
  name: string,
  options: { exact?: boolean } = {}
) {
  await expect(page.getByRole("heading", { name, exact: options.exact })).toBeVisible({
    timeout: routeReadyTimeoutMs
  });
}

async function expectNoForbiddenVisibleCopy(page: Page) {
  const text = await page.locator("main").innerText({ timeout: routeReadyTimeoutMs });
  for (const term of forbiddenVisibleCopy) {
    expect(text).not.toContain(term);
  }
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

    await expect(page.getByRole("heading", { name: "Centrum pracy" })).toBeVisible();
    await expect(
      page.getByText("WILQ pokazuje tylko metryki i dowody z danych źródłowych.").first()
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dzisiejsze decyzje marketera" })).toBeVisible();
    await expect(page.getByText("Decyzje").first()).toBeVisible();
    await expect(page.getByText("Blokady").first()).toBeVisible();
    await expect(page.getByText("Źródła danych:").first()).toBeVisible();
    await expect(page.getByText("Dowody w WILQ:").first()).toBeVisible();
    await expect(page.getByText(/potwierdzonych śladów w WILQ/).first()).toBeVisible();
    await expect(page.getByText("Akcje do sprawdzenia").first()).toBeVisible();
    await expect(page.getByText(/bezpieczna akcja do sprawdzenia/).first()).toBeVisible();
    await expect(page.getByText("Przykładowe dowody")).toHaveCount(0);
    await expect(page.getByText(/ev_refresh_/)).toHaveCount(0);
    await expect(page.getByText(/act_review_merchant_feed_issues/)).toHaveCount(0);
    await expect(page.getByText(/^Evidence:/)).toHaveCount(0);
    await expect(page.getByText("Przykładowe evidence")).toHaveCount(0);
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
    await expect(page.getByText("Kopiuj polecenie").first()).toBeVisible();
    await expect(page.getByText("Context-pack: /api/codex/context-pack")).toHaveCount(0);
    await expect(page.getByText(/Wymiar:/)).toHaveCount(0);
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
    await expectNoForbiddenVisibleCopy(page);

    await expect
      .poll(() => apiResponses.includes("200 /api/dashboard/command-center"))
      .toBe(true);
    expect(apiResponses.every((entry) => entry.startsWith("200 "))).toBe(true);
  });

  test("ads doctor route exposes live metric-backed diagnostics", async ({ page }) => {
    await page.goto("/ads-doctor");

    await expectApiBackedRouteHeading(page, "Google Ads", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Google Ads" })).toBeVisible();
    await expect(page.getByText("Decyzja skondensowana")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Aktualny odczyt Ads" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pełny przegląd Ads" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pokaż pełny przegląd Ads" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Dowody i warunki przeglądu Ads" })).toHaveCount(0);
    await page.getByRole("button", { name: "Pokaż pełny przegląd Ads" }).click();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Najpierw sprawdź w Ads" })).toBeVisible();
    await expect(page.getByText("tryb: sprawdzenie przed zapisem zmian")).toBeVisible();
    await expect(page.getByText("Przejrzyj aktywność kampanii Google Ads").first()).toBeVisible();
    await expect(page.getByText("Budżety").first()).toBeVisible();
    await expect(page.getByText("Zablokowane wnioski i zapis zmian")).toBeVisible();
    await expect(page.getByText(/akcj/i).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki przeglądu Ads" })).toBeVisible();
    await expect(page.getByText(/ev_connector_google_ads_status/)).toHaveCount(0);
    await expect(page.getByText("Handoff blockera Ads")).toHaveCount(0);
    await expect(page.getByText(/handoff blockera OAuth/i)).toHaveCount(0);
    await expect(page.getByText("Read contract Ads")).toHaveCount(0);
    await expect(page.getByText("Search terms read-only")).toHaveCount(0);
    await expect(page.getByText("Campaign activity read contract")).toHaveCount(0);
    await expect(page.getByText("Evidence", { exact: true })).toHaveCount(0);
    await expect(page.getByText("configured", { exact: true })).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("custom segments route exposes segment candidates for review", async ({ page }) => {
    await page.goto("/ads-doctor/custom-segments");

    await expectApiBackedRouteHeading(page, "Segmenty z haseł", { exact: true });
    await expect(
      page.getByRole("heading", { name: "Status segmentów i dowodów z wyszukiwanych haseł" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer może przygotować teraz" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki segmentów" })).toBeVisible();
    await expect(page.getByText(/Wyszukiwane hasła|Brak danych o wyszukiwanych hasłach/).first()).toBeVisible();
    await expect(page.getByText(/nie twierdzi, że segment ma zasięg|rozmiar odbiorców/i).first()).toBeVisible();
    await expect(page.getByText(/audience size/i)).toHaveCount(0);
    await expect(page.getByText("Evidence Registry")).toHaveCount(0);
    await expect(page.getByText("Connector Refresh Runs")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("demand gen route exposes readiness blocker instead of generic registry", async ({ page }) => {
    await page.goto("/ads-doctor/demand-gen");

    await expectApiBackedRouteHeading(page, "Demand Gen", { exact: true });
    await expect(page.getByRole("heading", { name: "Demand Gen: brak kampanii do rekomendacji" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma wiedzieć przed planem Demand Gen" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki sprawdzenia Demand Gen" })).toBeVisible();
    await expect(page.getByText("kampanie Ads")).toBeVisible();
    await expect(page.getByText(/Brakujące dane: brak/).first()).toBeVisible();
    await expect(page.getByText(/akcj/i).first()).toBeVisible();
    await expect(page.getByText("Podgląd gotowości Demand Gen")).toBeVisible();
    await expect(page.getByText(/rekomendacja uruchomienia Demand Gen/i).first()).toBeVisible();
    await expect(page.getByText(/launchu/i)).toHaveCount(0);
    await expect(page.getByText("API-backed operating surface")).toHaveCount(0);
    await expect(page.getByText("Evidence Registry")).toHaveCount(0);
    await expect(page.getByText("Connector Refresh Runs")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("ga4 route exposes metric-backed workflow focus", async ({ page }) => {
    await page.goto("/ga4");

    await expectApiBackedRouteHeading(page, "GA4", { exact: true });
    await expect(page.getByRole("heading", { name: "Status GA4 / pomiar i jakość ruchu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Bezpieczny tryb analityki" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sprawdź GA4 w WILQ" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pełny przegląd GA4" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż pełny przegląd GA4" }).click();
    await expect(page.getByRole("heading", { name: "Dowody i warunki pomiaru GA4" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa GA4" })).toBeVisible();
    await expect(page.getByText("GA4: landing/source/campaign behavior")).toHaveCount(0);
    await expect(page.getByText("GA4: tracking/conversion readiness")).toHaveCount(0);
    await expect(page.getByText("Analytics Safety Gate")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("seo and content routes expose dedicated Content Diagnostics", async ({ page }) => {
    await page.goto("/content-planner");

    await expectApiBackedRouteHeading(page, "Treści", { exact: true });
    await expect(page.getByRole("heading", { name: "Stan danych treści" })).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Zachowaj istniejącą treść i przygotuj odświeżenie albo scalenie, zamiast pisać nowy tekst od zera."
      })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Adresy i podgląd" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż pełny przegląd treści" }).click();
    await expect(page.getByRole("heading", { name: "Dowody i warunki decyzji treści" })).toBeVisible();
    await expect(page.getByText("GSC: query/page matrix")).toHaveCount(0);
    await expect(page.getByText("WordPress: inventory protection")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa treści" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Akcje do sprawdzenia", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }).click();
    await expect(page.getByRole("heading", { name: "Przygotuj kolejkę odświeżenia treści ekologus.pl" }).first()).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("action detail route shows validation, evidence and change preview", async ({ page }) => {
    await page.goto("/actions/act_review_merchant_feed_issues");

    await expectApiBackedRouteHeading(page, "Przygotuj kolejkę przeglądu feedu Merchant Center");
    await expect(page.getByRole("heading", { name: "Dowody i diagnoza" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Podgląd zmian" })).toBeVisible();
    await expect(page.getByText("Dowody: 1 dowód źródłowy")).toBeVisible();
    await expect(page.getByText(/ev_refresh_refresh_google_merchant_center/)).toHaveCount(0);
    await expect(page.getByText(/^Evidence:/)).toHaveCount(0);
    await page.getByRole("button", { name: "Generuj podgląd" }).click();
    await expect(page.getByText("Podgląd zmian wygenerowany").first()).toBeVisible();
    await expect(page.getByText("Jawne potwierdzenie podglądu")).toBeVisible();
    await page.getByRole("button", { name: "Potwierdź podgląd" }).click();
    await expect(page.getByText("Podgląd potwierdzony").first()).toBeVisible();
    await expect(page.getByText(/Nie zapisano zmian w zewnętrznych systemach/).first()).toBeVisible();
    await expect(page.getByText("Sprawdź efekt", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Sprawdź efekt" }).click();
    await expect(page.getByText("Sprawdzenie efektu zapisane").first()).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("actions route starts with actions instead of registry dumps", async ({ page }) => {
    await page.goto("/actions");

    await expectApiBackedRouteHeading(page, "Akcje do sprawdzenia", { exact: true });
    await expect(page.getByRole("heading", { name: "Najważniejsze na start" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pozostałe akcje" })).toBeVisible();
    await expect(page.getByText("Do sprawdzenia", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Odnow Google Ads OAuth refresh token")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "OPPORTUNITIES" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Connector Refresh Runs" })).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("workflows route exposes decision-backed operator workflows", async ({ page }) => {
    await page.goto("/workflows");

    await expectApiBackedRouteHeading(page, "Procesy WILQ");
    await expect(page.getByRole("heading", { name: "Procesy decyzyjne" })).toBeVisible();
    await expect(page.getByText("Plan dnia WILQ")).toBeVisible();
    await expect(page.getByText("Feed Merchant")).toBeVisible();
    await expect(page.getByText("Treści z GSC")).toBeVisible();
    await expect(page.getByText("Ocena Ads")).toBeVisible();
    await page.getByRole("button", { name: /Pokaż wszystkie procesy/ }).click();
    await expect(page.getByText("Widoczność lokalna Localo")).toBeVisible();
    await expect(page.getByText("decyzje").first()).toBeVisible();
    await expect(page.getByText("akcje").first()).toBeVisible();
    await expect(page.getByText("średnie ryzyko").first()).toBeVisible();
    await expect(page.getByText("wilq-daily-command")).toHaveCount(0);
    await expect(page.getByText("daily_command")).toHaveCount(0);
    await expect(page.getByText("local_ranking_rows")).toHaveCount(0);
    await expect(page.getByText("Workflow definition runs against WILQ API")).toHaveCount(0);
    await expect(page.getByText("Fetch WILQ API context")).toHaveCount(0);
    await expect(page.getByText("Rejestr workflowów")).toHaveCount(0);
    await expect(page.getByText("Workflowy WILQ")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("knowledge route maps source knowledge to decisions", async ({ page }) => {
    await page.goto("/knowledge");

    await expectApiBackedRouteHeading(page, "Baza wiedzy WILQ");
    await expect(page.getByRole("heading", { name: "Co ta wiedza zmienia w decyzjach" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż pełną mapę wiedzy" }).click();
    await expect(page.getByText("Powiązania")).toBeVisible();
    await expect(page.getByText("Wiedza użyta w decyzji").first()).toBeVisible();
    await expect(page.getByText("Zablokowane obietnice").first()).toBeVisible();
    await page.getByRole("button", { name: "Pokaż źródła wiedzy" }).click();
    await expect(page.getByText("Ślady źródłowe").first()).toBeVisible();
    await page.getByRole("button", { name: "Pokaż zasady pracy" }).click();
    await expect(page.getByText("Wymagane dowody").first()).toBeVisible();
    await expect(page.getByText("Ocena Ads").first()).toBeVisible();
    await expect(page.getByText("Feed Merchant").first()).toBeVisible();
    await expect(page.getByText("Knowledge Cards")).toHaveCount(0);
    await expect(page.getByText("Machine-Readable Playbooks")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("merchant route renders live Merchant Diagnostics evidence links", async ({ page }) => {
    const merchantDiagnosticsResponse = page.waitForResponse(
      (response) => {
        const url = new URL(response.url());
        return url.pathname === "/api/merchant/diagnostics" && response.status() === 200;
      },
      { timeout: 60_000 }
    );
    await page.goto("/merchant");
    const merchantDiagnostics = await (await merchantDiagnosticsResponse).json();

    await expectApiBackedRouteHeading(page, "Merchant Center", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Merchant Center" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pierwszy problem Merchant do sprawdzenia" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż pełny przegląd Merchant" }).click();
    await expect(page.getByText("Dowody i warunki przeglądu Merchant")).toBeVisible();
    await expect(page.getByText("Merchant Center: feed/product health")).toHaveCount(0);
    await expect(page.getByText("Merchant Center: kolejka feed/product issues")).toHaveCount(0);
    await expect(page.getByText("Zgłoszenia", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Affected", { exact: true })).toHaveCount(0);
    await expect(page.getByText("configured", { exact: true })).toHaveCount(0);
    await expect(page.getByText("Evidence", { exact: true })).toHaveCount(0);
    await expect(page.getByText(merchantDiagnostics.connector_status_label)).toBeVisible();
    await expect(page.getByText("metryki feedu dostępne")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Gotowość próbek produktów" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Wpływ ceny produktu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Akcje do sprawdzenia" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }).click();
    await expect(
      page.getByRole("heading", { name: "Przygotuj kolejkę przeglądu feedu Merchant Center" }).first()
    ).toBeVisible();
    await expect(page.getByText(/Zapis zmian:.*zablokowany/).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa feedu" })).toBeVisible();

    await expect(page.getByText(/ev_refresh_refresh_google_merchant_center/)).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
    const evidenceLink = page.getByRole("link", { name: "dowód 1" }).first();
    await expect(evidenceLink).toBeVisible();
    await evidenceLink.click();
    await expect(page.getByRole("heading", { name: /Merchant Center/ })).toBeVisible();
    await expect(page.getByText("Źródło: Merchant Center")).toBeVisible();
    await page.getByRole("button", { name: "Pokaż szczegóły techniczne dowodu" }).click();
    await expect(page.getByText(/ID dowodu: ev_refresh_refresh_google_merchant_center/)).toBeVisible();
  });

  test("localo route exposes aggregate facts without unsupported local claims", async ({ page }) => {
    await page.goto("/localo");

    await expectApiBackedRouteHeading(page, "Localo", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Localo / widoczność lokalna" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma wiedzieć o Localo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki diagnozy Localo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa Localo i profilu firmy w Google" })).toBeVisible();
    await expect(
      page.getByText(/Przejrzyj agregaty widoczności lokalnej z Localo/)
    ).toBeVisible();
    await expect(page.getByText(/lista lokalizacji/)).toBeVisible();
    await expect(page.getByText(/rankingi lokalne/)).toBeVisible();
    await expect(page.getByText(/opinie/).first()).toBeVisible();
    await expect(page.getByText(/widoczność konkurencji/).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dane Localo w WILQ" })).toBeVisible();
    await expect(page.getByText(/LOCALO_ACCESS_TOKEN/)).toHaveCount(0);
    await expect(page.getByText(/Dokończ Localo access/)).toHaveCount(0);
    await expect(page.getByText(/Local Visibility Focus/)).toHaveCount(0);
    await expect(page.getByText("Taktyki z WILQ API")).toHaveCount(0);
    await expect(page.getByText("Metric facts")).toHaveCount(0);
    await expect(page.getByText("24 Taktyki")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });

  test("ahrefs route exposes authority context and gap safety state", async ({ page }) => {
    await page.goto("/ahrefs");

    await expectApiBackedRouteHeading(page, "Ahrefs", { exact: true });
    await expect(page.getByRole("heading", { name: "Status Ahrefs / dowody SEO" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma wiedzieć o Ahrefs" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki analizy Ahrefs" })).toBeVisible();
    await expect(page.getByText(/odczyt autorytetu Ahrefs|metryki Ahrefs dostępne/).first()).toBeVisible();
    await expect(page.getByText(/Przejrzyj rekordy luk Ahrefs|Brak typed gap records/).first()).toBeVisible();
    await expect(page.getByText(/ocena domeny Ahrefs|brakujące dane/).first()).toBeVisible();
    await expect(page.getByText("Rekordy luk").first()).toBeVisible();
    await expect(page.getByText(/gotowe|zablokowane/).first()).toBeVisible();
    await expect(page.getByText(/strony konkurencji/).first()).toBeVisible();
    await expect(page.getByText(/competitor_page/)).toHaveCount(0);
    await expect(page.getByText(/Strona konkurencji:|rekordy luk treści/).first()).toBeVisible();
    await expect(page.getByText(/wzrost autorytetu/).first()).toBeVisible();
    await expect(page.getByText("Evidence Registry")).toHaveCount(0);
    await expect(page.getByText("Connector Refresh Runs")).toHaveCount(0);
    await expect(page.getByText("API-backed operating surface")).toHaveCount(0);
    await expectNoForbiddenVisibleCopy(page);
  });
});
