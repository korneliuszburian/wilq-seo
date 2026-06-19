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
      page.getByRole("heading", { name: "Przejrzyj produkty z problemami w Merchant Center" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Ułóż kolejkę refresh/merge/create dla treści SEO" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Sprawdź jakość ruchu i landing page w GA4" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Przejrzyj kampanie Google Ads z live metryk" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Localo: MCP access działa, brak jeszcze ranking/GBP facts" })
    ).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Plan działań marketera" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Blockery i świeżość źródeł" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Demo dla marketera" })).toHaveCount(0);
    await expect(page.getByText("act_review_merchant_feed_issues").first()).toBeVisible();
    await expect(page.getByText("Przejrzyj kampanie Google Ads z live metryk")).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "01-command-center-action-plan.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/merchant", "/api/merchant/diagnostics");
    await expect(page.getByRole("heading", { name: "Merchant Center", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma zrobić teraz z feedem" })).toBeVisible();
    await expect(page.getByText("Dowody i ograniczenia Merchant")).toBeVisible();
    await expect(page.getByText("Zgłoszenia", { exact: true })).toBeVisible();
    await expect(
      page.getByText(/missing_potentially_required_attribute|availability_updated/).first()
    ).toBeVisible();
    await expect(page.getByText(/item_level_issue_count: \d+/).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "act_review_merchant_feed_issues" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /ev_refresh_refresh_google_merchant_center/ }).first()).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "02-merchant-feed-issues.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/content-planner", "/api/content/diagnostics");
    await expect(page.getByRole("heading", { name: "Content Planner", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status SEO / Content" })).toBeVisible();
    await expect(page.getByRole("link", { name: "act_prepare_content_refresh_queue" }).first()).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "03-content-planner-queue.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/ga4", "/api/ga4/diagnostics");
    await expect(page.getByRole("heading", { name: "GA4", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w jakości ruchu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia GA4" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Brama bezpieczeństwa GA4" })).toBeVisible();
    await expect(page.getByText("GA4: landing/source/campaign behavior")).toHaveCount(0);
    await expect(page.getByText("Analytics Safety Gate")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "act_review_ga4_tracking_quality" }).first()).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "04-ga4-landing-quality.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/ads-doctor", "/api/ads/diagnostics");
    await expect(page.getByRole("heading", { name: "Ads Doctor" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Co marketer ma sprawdzić teraz w Google Ads" })
    ).toBeVisible();
    await expect(page.getByText("Przejrzyj aktywność kampanii Google Ads")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Ads" })).toBeVisible();
    await page.screenshot({
      path: path.join(runDir, "05-ads-live-campaign-metrics.png"),
      fullPage: true,
    });

    await gotoAndWaitForApi(page, "/localo", "/api/localo/diagnostics");
    await expect(page.getByRole("heading", { name: "Localo", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Status Localo / MCP access" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co marketer ma wiedzieć o Localo" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dowody i ograniczenia Localo" })).toBeVisible();
    await expect(page.getByText(/Localo access działa; brakuje ranking\/GBP facts/)).toBeVisible();
    await expect(page.getByText(/MCP initialize zwrócił 200/)).toBeVisible();
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
        "- 03-content-planner-queue.png",
        "- 04-ga4-landing-quality.png",
        "- 05-ads-live-campaign-metrics.png",
        "- 06-localo-access-status.png",
        "",
      ].join("\n"),
      "utf-8"
    );
  });
});
