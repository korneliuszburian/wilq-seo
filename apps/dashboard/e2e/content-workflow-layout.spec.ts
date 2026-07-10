import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-workflow");

test.describe("WILQ content workflow layout proof", () => {
  test("puts the page authoring workbench before legacy workflow details", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });
    await page.setViewportSize({ width: 1536, height: 1024 });

    const queueResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/content/work-items/queue" && response.status() === 200;
    });
    const snapshotResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return (
        url.pathname.startsWith("/api/content/work-items/") &&
        url.pathname.endsWith("/snapshot") &&
        response.status() === 200
      );
    });
    await page.goto("/content-workflow");
    await queueResponse;
    await snapshotResponse;

    await expect(page.getByRole("heading", { name: "Treści: praca nad stroną" })).toBeVisible();
    await expect(page.getByText("Public", { exact: true })).toBeVisible();
    await expect(page.getByText("ekologus.pl", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Dev", { exact: true })).toBeVisible();
    await expect(
      page.getByText("ekologus.dev.proudsite.pl", { exact: true }).first()
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Aktualna strona" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sygnały i braki" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Dev draft / ACF" })).toBeVisible();
    await expect(page.getByLabel("Cel dev do podglądu")).toBeVisible();
    await expect(page.getByText("Porównaj sekcje dev z propozycją szkicu")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Tekst sekcji do szkicu" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Podgląd sekcji na devie" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Źródła i claimy" })).toBeVisible();
    await expect(
      page.getByText("Szczegóły workflow, kolejka i audyt techniczny")
    ).toBeVisible();

    const titleBox = await page
      .getByRole("heading", { name: "Treści: praca nad stroną" })
      .boundingBox();
    const mapBox = await page
      .getByRole("heading", { name: "Aktualna strona" })
      .boundingBox();
    const editorBox = await page
      .getByRole("heading", { name: "Tekst sekcji do szkicu" })
      .boundingBox();
    const detailsBox = await page
      .getByText("Szczegóły workflow, kolejka i audyt techniczny")
      .boundingBox();

    expect(titleBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      mapBox?.y ?? Number.POSITIVE_INFINITY
    );
    expect(mapBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      editorBox?.y ?? Number.POSITIVE_INFINITY
    );
    expect(editorBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      detailsBox?.y ?? Number.POSITIVE_INFINITY
    );

    await page.screenshot({
      path: path.join(runDir, "content-workflow-page-authoring-workbench.png"),
      fullPage: true,
    });
  });
});
