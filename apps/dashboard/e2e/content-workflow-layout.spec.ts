import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-workflow");

test.describe("WILQ content workflow layout proof", () => {
  test("puts the current source blocker before authoring details", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });
    await page.setViewportSize({ width: 1536, height: 1024 });

    const queueStartedAt = Date.now();
    const queueResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/content/work-items/queue" && response.status() === 200;
    });
    await page.goto("/content-workflow");
    await queueResponse;
    expect(Date.now() - queueStartedAt).toBeLessThan(5_000);

    await expect(
      page.getByRole("heading", { name: "Źródła treści: dane treści wymagają odświeżenia" })
    ).toBeVisible();
    await expect(page.getByText("Gotowe do pracy: 0 z 2 tematów")).toBeVisible();
    await expect(page.getByRole("heading", { name: "WILQ blokuje pisanie tego tematu" })).toBeVisible();
    await expect(
      page.getByText("Uruchom odczyt danych dla wskazanych źródeł", { exact: false }).first()
    ).toBeVisible();
    await expect(page.getByText("Ładowanie stanu WILQ")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Treści: praca nad stroną" })).toHaveCount(0);

    await page.screenshot({
      path: path.join(runDir, "content-workflow-freshness-blocker.png"),
      fullPage: true,
    });
  });
});
