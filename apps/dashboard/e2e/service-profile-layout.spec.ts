import { expect, test } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-service-profile");

test.describe("WILQ service profile layout proof", () => {
  test("shows owner review focus before full service knowledge catalog", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

    const profileResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return url.pathname === "/api/content/service-profile" && response.status() === 200;
    });
    await page.goto("/service-profile");
    await profileResponse;

    await expect(page.getByRole("heading", { name: "Profil usług Ekologus" })).toBeVisible();
    await expect(page.getByText("Wiedza Ekologus: co dziś sprawdzić")).toBeVisible();
    await expect(page.getByText("Pierwszy review item")).toBeVisible();
    await expect(page.getByRole("button", { name: "Pokaż pełny przegląd wiedzy" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Gotowość zatwierdzenia wiedzy" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Audyt pokrycia wiedzy" })).toHaveCount(0);

    const firstReviewBox = await page.getByText("Pierwszy review item").boundingBox();
    const fullReviewButtonBox = await page
      .getByRole("button", { name: "Pokaż pełny przegląd wiedzy" })
      .boundingBox();
    expect(firstReviewBox?.y ?? Number.POSITIVE_INFINITY).toBeLessThan(
      fullReviewButtonBox?.y ?? Number.POSITIVE_INFINITY
    );

    await page.screenshot({
      path: path.join(runDir, "service-profile-review-first.png"),
      fullPage: true,
    });
  });
});
