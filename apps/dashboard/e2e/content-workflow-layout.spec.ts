import { expect, test } from "@playwright/test";

test.describe("WILQ marketer content workspace", () => {
  test("opens the marketer content entry without queue authority or browser writes", async ({ page }) => {
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

    await page.goto("/content-workflow");

    await expect(page.getByRole("heading", { name: "Tworzenie i odświeżanie treści" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Wybierz stronę/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Zacznij od briefu/ })).toBeVisible();
    expect(queueRequests).toBe(0);
    expect(contentWrites).toEqual([]);
  });

});
