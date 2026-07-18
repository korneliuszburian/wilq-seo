import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-knowledge");

test.describe("WILQ knowledge layout proof", () => {
  test("shows one decision impact before full knowledge catalog", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

    const operatingMapResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/knowledge/operating-map" && response.status() === 200;
    });
    await page.goto("/knowledge");
    await operatingMapResponse;

    await expect(page.getByRole("heading", { name: "Źródła i wiedza", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Realne materiały i fakty Ekologusa" })).toBeVisible();
    await expect(page.getByText("15 materiałów w manifeście Ekologusa")).toBeVisible();
    await expect(page.getByText("import pending")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Najbliższy krok źródłowy" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co blokuje produkcję treści" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejka sprawdzania wiedzy" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sprawdź kartę" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Pokaż kartę" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Zobacz pełną kolejkę" })).toBeVisible();
    await expect(page.getByText("Knowledge Cards")).toHaveCount(0);
    await expect(page.getByText("Machine-Readable Playbooks")).toHaveCount(0);

    const primaryDecisionBox = await page
      .getByRole("heading", { name: "Najbliższy krok źródłowy" })
      .boundingBox();
    const fullMapBox = await page
      .getByRole("button", { name: "Zobacz pełną kolejkę" })
      .boundingBox();

    expect(primaryDecisionBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      fullMapBox?.y ?? Number.POSITIVE_INFINITY
    );

    await page.screenshot({
      path: path.join(runDir, "knowledge-decision-first.png"),
      fullPage: true,
    });
  });
});
