import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-workflow");

test.describe("WILQ content workflow layout proof", () => {
  test("puts operator decisions before queue, proof and WordPress readiness", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

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

    await expect(page.getByRole("heading", { name: "Workflow treści bez slopu" })).toBeVisible();
    await expect(page.getByText("Workflow treści: co dziś zrobić")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Decyzje operatora" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Kolejka tematów" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Co WILQ już potwierdził" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "WordPress: szkic bez publikacji" })).toBeVisible();

    const decisionsBox = await page
      .getByRole("heading", { name: "Decyzje operatora" })
      .boundingBox();
    const queueBox = await page
      .getByRole("heading", { name: "Kolejka tematów" })
      .boundingBox();
    const proofBox = await page
      .getByRole("heading", { name: "Co WILQ już potwierdził" })
      .boundingBox();
    const wordpressBox = await page
      .getByRole("heading", { name: "WordPress: szkic bez publikacji" })
      .boundingBox();

    expect(decisionsBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      queueBox?.y ?? Number.POSITIVE_INFINITY
    );
    expect(decisionsBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      proofBox?.y ?? Number.POSITIVE_INFINITY
    );
    expect(decisionsBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      wordpressBox?.y ?? Number.POSITIVE_INFINITY
    );

    await page.screenshot({
      path: path.join(runDir, "content-workflow-decisions-first.png"),
      fullPage: true,
    });
  });
});
