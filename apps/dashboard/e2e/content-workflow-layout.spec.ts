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

    // The first entry render after a cold API start can exceed the default
    // expect timeout when verify.sh runs this suite right after the full
    // backend gate on a loaded workstation. Wait for the actual entry heading
    // with a longer bound; the button assertions below stay on the default.
    await expect(page.getByRole("heading", { name: "Tworzenie i odświeżanie treści" })).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: /Wybierz stronę/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Zacznij od briefu/ })).toBeVisible();
    expect(queueRequests).toBe(0);
    expect(contentWrites).toEqual([]);
  });

});
