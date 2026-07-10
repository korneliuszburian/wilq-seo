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

test.describe("WILQ dashboard marketer demo proof", () => {
  test("captures API-backed demo path with action plan and blockers", async ({ page }) => {
    test.setTimeout(90000);
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

    await gotoAndWaitForApi(page, "/command-center", "/api/dashboard/command-center");
    await expect(page.getByRole("heading", { name: "Dzisiejsze decyzje marketera" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Przejrzyj kolejkę problemów Merchant Center" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Przejrzyj kolejkę SEO z GSC i WordPress" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "GA4: pomiar i jakość ruchu do kontroli" })
    ).toBeVisible();
    await expect(page.getByText("Czego nie twierdzimy").first()).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Localo: MCP access działa, brak jeszcze ranking/GBP facts" })
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Plan działań marketera" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Demo dla marketera" })).toHaveCount(0);
    await expect(page.getByText("Akcje do sprawdzenia").first()).toBeVisible();
    await expect(page.getByText("1 bezpieczna akcja do sprawdzenia").first()).toBeVisible();
    await expect(page.getByText("act_review_merchant_feed_issues")).toHaveCount(0);
    await expect(page.getByText("Czego nie twierdzimy").first()).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "01-command-center-action-plan.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/merchant", "/api/merchant/diagnostics");
    await expect(page.getByRole("heading", { name: "Merchant Center", exact: true })).toBeVisible();
    await expect(page.getByText("Merchant: co dziś zrobić")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejność pracy" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Czego nie obiecywać" })).toBeVisible();
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

    await gotoAndWaitForApi(page, "/content-workflow", "/api/content/diagnostics");
    await expect(page.getByRole("heading", { name: "Treści", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Adresy i podgląd" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Stan danych treści" })).toBeVisible();
    const selectedDecisionBox = await page
      .getByRole("heading", { name: "Adresy i podgląd" })
      .boundingBox();
    const dataStatusBox = await page
      .getByRole("heading", { name: "Stan danych treści" })
      .boundingBox();
    expect(selectedDecisionBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      dataStatusBox?.y ?? Number.POSITIVE_INFINITY
    );
    await expect(page.getByText("Treści: co dziś zrobić")).toHaveCount(0);
    await page.getByRole("button", { name: "Pokaż akcje do sprawdzenia" }).click();
    await expect(page.getByRole("heading", { name: "Przygotuj kolejkę odświeżenia treści ekologus.pl" }).first()).toBeVisible();
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
    await expect(page.getByRole("heading", { name: "Google Ads", exact: true })).toBeVisible();
    await expect(page.getByText("Google Ads: co dziś zrobić")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejność pracy" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Pełny przegląd Ads" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pokaż pełny przegląd Ads" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki przeglądu Ads" })).toHaveCount(0);
    await page.getByRole("button", { name: "Pokaż pełny przegląd Ads" }).click();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).toBeVisible();
    await expect(page.getByText("Przejrzyj aktywność kampanii Google Ads").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i warunki przeglądu Ads" })).toBeVisible();
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
