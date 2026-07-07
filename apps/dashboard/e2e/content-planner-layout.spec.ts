import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-planner");

test.describe("WILQ content planner layout proof", () => {
  test("puts one selected content decision before status and technical detail", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

    const diagnosticsResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/content/diagnostics" && response.status() === 200;
    });
    await page.goto("/content-planner");
    await diagnosticsResponse;

    await expect(page.getByRole("heading", { name: "Treści", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Adresy i podgląd" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Stan danych treści" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Czy można pisać?" })).toBeVisible();
    await expect(page.getByText("Treści: co dziś zrobić")).toHaveCount(0);
    await expect(page.getByText("Najpierw decyzja contentowa, potem szkic")).toHaveCount(0);
    await expect(page.getByText("Kolejność pracy")).toHaveCount(0);

    const selectedDecisionBox = await page
      .getByRole("heading", { name: "Adresy i podgląd" })
      .boundingBox();
    const dataStatusBox = await page
      .getByRole("heading", { name: "Stan danych treści" })
      .boundingBox();
    const preflightBox = await page
      .getByRole("heading", { name: "Czy można pisać?" })
      .boundingBox();

    expect(selectedDecisionBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      dataStatusBox?.y ?? Number.POSITIVE_INFINITY
    );
    expect(selectedDecisionBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      preflightBox?.y ?? Number.POSITIVE_INFINITY
    );

    await page.screenshot({
      path: path.join(runDir, "content-planner-decision-first.png"),
      fullPage: true,
    });
  });
});
