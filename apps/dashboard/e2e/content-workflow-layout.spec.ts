import { expect, test, type Page } from "@playwright/test";

const evidenceBoundUrl = "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/";

async function selectEvidenceBoundPage(page: Page) {
  const apiPort = process.env.WILQ_E2E_API_PORT ?? "8875";
  const response = await page.request.get(
    `http://127.0.0.1:${apiPort}/api/content/workflow-entry`
  );
  expect(response.ok()).toBe(true);
  const entry = (await response.json()) as {
    recommendations: Array<{ url: string; work_item_id: string }>;
  };
  const recommendation = entry.recommendations.find((item) => item.url === evidenceBoundUrl);
  expect(recommendation?.work_item_id).toBeTruthy();
  return recommendation!.work_item_id;
}

test.describe("WILQ marketer content workspace", () => {
  test("opens an exact selected page without queue authority or browser writes", async ({ page }) => {
    const workItemId = await selectEvidenceBoundPage(page);
    let queueRequests = 0;
    const contentWrites: string[] = [];
    await page.route("**/api/content/work-items/queue*", async (route) => {
      queueRequests += 1;
      await route.continue();
    });
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.pathname.startsWith("/api/content/") && !["GET", "HEAD", "OPTIONS"].includes(request.method())) {
        contentWrites.push(`${request.method()} ${url.pathname}`);
      }
    });

    await page.goto(`/content-workflow/${workItemId}`);

    await expect(page.getByTestId("content-text-workspace")).toBeVisible();
    await expect(page.getByTestId("content-text-workspace").getByRole("heading", { level: 1, name: /BDO.*MUSI WIEDZIEĆ PRZEDSIĘBIORCA/i })).toBeVisible();
    await expect(page.getByText(evidenceBoundUrl, { exact: true })).toBeVisible();
    await expect(page.getByTestId("content-document-workspace-error")).toHaveCount(0);
    expect(queueRequests).toBe(0);
    expect(contentWrites).toEqual([]);
  });

  test("starts from marketer intent instead of the retired workflow workbench", async ({ page }) => {
    const contentWrites: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.pathname.startsWith("/api/content/") && !["GET", "HEAD", "OPTIONS"].includes(request.method())) {
        contentWrites.push(`${request.method()} ${url.pathname}`);
      }
    });

    await page.goto("/content-workflow");

    await expect(page.getByRole("heading", { name: "Tworzenie i odświeżanie treści" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Wybierz stronę/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Zacznij od briefu/ })).toBeVisible();
    await expect(page.getByTestId("content-workflow-task-map")).toHaveCount(0);
    await expect(page.getByTestId("content-workflow-technical-audit")).toHaveCount(0);
    expect(contentWrites).toEqual([]);
  });
});
