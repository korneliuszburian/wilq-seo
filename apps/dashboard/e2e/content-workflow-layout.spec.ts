import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-workflow");

test.describe("WILQ content workflow layout proof", () => {
  test("shows a decision, proof context and safe authoring next step", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });
    await page.setViewportSize({ width: 1536, height: 1024 });

    const queueStartedAt = Date.now();
    const queueResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/content/work-items/queue" && response.status() === 200;
    });
    await page.goto("/content-workflow");
    const queuePayload = (await (await queueResponse).json()) as {
      queue_status?: string;
      freshness_assessment?: { requires_refresh?: boolean };
    };
    expect(Date.now() - queueStartedAt).toBeLessThan(5_000);

    if (queuePayload.queue_status === "blocked" && queuePayload.freshness_assessment?.requires_refresh) {
      await expect(page.getByRole("heading", { name: "Workflow treści bez slopu" })).toBeVisible();
      await expect(page.getByRole("heading", { name: /Źródła treści:/ })).toBeVisible();
      await expect(page.getByRole("status").getByText(/Następny bezpieczny krok:/)).toBeVisible();
      await expect(page.getByText(/Nie pokazujemy decyzji bez kontraktów API/)).toHaveCount(0);
      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth
      );
      expect(hasHorizontalOverflow).toBe(false);
      await page.screenshot({
        path: path.join(runDir, "content-workflow-blocked-state.png"),
        fullPage: true,
      });
      return;
    }

    await expect(page.getByRole("heading", { name: "Treści: praca nad stroną" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Strona główna ekologus.pl", exact: true }).first()
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "https://www.ekologus.pl/" })).toBeVisible();
    await expect(page.getByRole("button", { name: "odśwież istniejącą treść" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Aktualna strona" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sygnały i braki" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dev draft / ACF" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Przygotuj podgląd draftu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Źródła i twierdzenia" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Źródła treści: dane treści wymagają odświeżenia" })
    ).toHaveCount(0);
    await expect(page.getByText("Gotowe do pracy: 0 z 2 tematów")).toHaveCount(0);
    await expect(page.getByText("Ładowanie stanu WILQ")).toHaveCount(0);
    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(hasHorizontalOverflow).toBe(false);

    await page.screenshot({
      path: path.join(runDir, "content-workflow-freshness-blocker.png"),
      fullPage: true,
    });
  });
});
