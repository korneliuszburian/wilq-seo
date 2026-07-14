import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-demo");

async function gotoAndWaitForApi(page: Page, route: string, apiPath: string) {
  const apiResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return url.pathname === apiPath && response.status() === 200;
  });
  await page.goto(route);
  await apiResponse;
}

async function expectNoVisibleTechnicalIds(page: Page) {
  const matches = page.getByText(/\b(?:act|ev)_[a-z0-9_]+\b/);
  const matchCount = await matches.count();
  for (let index = 0; index < matchCount; index += 1) {
    await expect(matches.nth(index)).toBeHidden();
  }
}

test.describe("WILQ dashboard marketer demo proof", () => {
  test("captures API-backed demo path with action plan and blockers", async ({ page }) => {
    test.setTimeout(90000);
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

    await gotoAndWaitForApi(page, "/command-center", "/api/dashboard/command-center");
    await expect(page.getByRole("heading", { name: "Dzisiaj" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Następna najlepsza praca" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Blokady, których nie obchodź" })).toBeVisible();
    await expect(page.getByText("Kolejka dziś")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Nie wolno dziś twierdzić" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Localo: MCP access działa, brak jeszcze ranking/GBP facts" })
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Plan działań marketera" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Demo dla marketera" })).toHaveCount(0);
    await expect(page.getByText("akcji do sprawdzenia").first()).toBeVisible();
    await expect(page.getByText("act_review_merchant_feed_issues")).toHaveCount(0);
    await page.screenshot({
      path: path.join(runDir, "01-command-center-action-plan.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/merchant", "/api/merchant/diagnostics");
    await expect(page.getByRole("heading", { name: "Produkty", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Najważniejsza praca teraz" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co blokuje decyzję" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Nie wolno dziś twierdzić" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż pełny przegląd Merchant" }).click();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma zrobić teraz z plikiem produktowym" }).first()
    ).toBeVisible();
    await expect(page.getByText("Dowody i warunki przeglądu Merchant")).toBeVisible();
    await expect(page.getByText("Zgłoszenia", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Zgłoszenia", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/missing_potentially_required_attribute|availability_updated/)).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Gotowość próbek produktów" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }).click();
    await expect(page.getByRole("heading", { name: "Przygotuj kolejkę przeglądu pliku produktowego Merchant Center" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "dowód 1" }).first()).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "02-merchant-feed-issues.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/content-workflow", "/api/content/work-items/queue");
    await expect(page.getByRole("heading", { name: "Treści: praca nad stroną", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Aktualna strona" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sygnały i braki" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dev draft / ACF" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Podgląd na devie", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Źródła i twierdzenia" })).toBeVisible();
    const previewButton = page.getByRole("button", { name: "Przygotuj podgląd draftu" });
    const previewButtonBox = await previewButton.boundingBox();
    const evidenceBox = await page
      .getByRole("heading", { name: "Źródła i twierdzenia" })
      .boundingBox();
    expect(previewButtonBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      evidenceBox?.y ?? Number.POSITIVE_INFINITY
    );
    await expect(previewButton).toBeVisible();
    await expect(
      page.getByText("Ten krok przygotowuje wyłącznie podgląd. Zapis wymaga osobnego zatwierdzenia.")
    ).toBeVisible();
    await expectNoVisibleTechnicalIds(page);
    await page.screenshot({
      path: path.join(runDir, "03-content-workflow-workbench.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/ga4", "/api/ga4/diagnostics");
    await expect(page.getByRole("heading", { name: "GA4", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w jakości ruchu" })).toBeVisible();
    await page.getByRole("button", { name: "Pokaż pełny przegląd GA4" }).click();
    await expect(page.getByRole("heading", { name: "Dowody i warunki pomiaru GA4" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa GA4" })).toBeVisible();
    await expect(page.getByText("GA4: landing/source/campaign behavior")).toHaveCount(0);
    await expect(page.getByText("Analytics Safety Gate")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Sprawdź GA4 w WILQ" }).first()).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "04-ga4-landing-quality.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/ads-doctor", "/api/ads/diagnostics");
    await expect(page.getByRole("heading", { name: "Reklamy i pomiar", exact: true })).toBeVisible();
    await expect(page.getByText("Najpierw pomiar", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "ROAS, przychód, waste i konwersje są zablokowane do czasu potwierdzenia danych."
      })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejka diagnostyczna" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Bezpieczne tryby pracy" })).toBeVisible();
    await expectNoVisibleTechnicalIds(page);
    await page.screenshot({
      path: path.join(runDir, "05-ads-live-campaign-metrics.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/localo", "/api/localo/diagnostics");
    await expect(page.getByRole("heading", { name: "Localo", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status Localo i widoczność lokalna" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma wiedzieć o Localo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki diagnozy Localo" })).toBeVisible();
    await expect(
      page.getByText(/Przejrzyj agregaty widoczności lokalnej z Localo/)
    ).toBeVisible();
    await expect(page.getByText(/rankingi lokalne/).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dane Localo w WILQ" })).toBeVisible();
    await expect(page.getByText(/Dokończ Localo access/)).toHaveCount(0);
    await expect(page.getByText(/Local Visibility Focus/)).toHaveCount(0);
    await page.screenshot({
      path: path.join(runDir, "06-localo-access-status.png"),
      fullPage: true,
    });

    await fs.writeFile(
      path.join(runDir, "README.md"),
      [
        "# WILQ dashboard demo proof",
        "",
        "Local browser proof generated by Playwright.",
        "",
        "- 01-command-center-action-plan.png",
        "- 02-merchant-feed-issues.png",
        "- 03-content-workflow-workbench.png",
        "- 04-ga4-landing-quality.png",
        "- 05-ads-live-campaign-metrics.png",
        "- 06-localo-access-status.png",
        "",
      ].join("\n"),
      "utf-8"
    );
  });
});
