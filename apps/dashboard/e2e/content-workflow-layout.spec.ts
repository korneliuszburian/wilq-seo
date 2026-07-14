import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

import type { ContentWorkItemWorkflowSnapshotResponse } from "../src/lib/api";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-workflow");

const viewports = [
  { label: "desktop", width: 1440, height: 900 },
  { label: "mobile", width: 390, height: 844 }
] as const;

test.describe("WILQ content workflow layout proof", () => {
  test("keeps one API-owned authoring step useful on desktop and mobile", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });
    let readyViewportCount = 0;

    const contentWriteRequests: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (
        url.pathname.startsWith("/api/content/") &&
        !["GET", "HEAD", "OPTIONS"].includes(request.method())
      ) {
        contentWriteRequests.push(`${request.method()} ${url.pathname}`);
      }
    });

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      const queueResponse = page.waitForResponse((response) => {
        const url = new URL(response.url());
        return url.pathname === "/api/content/work-items/queue" && response.status() === 200;
      });
      await page.goto("/content-workflow");
      const queuePayload = (await (await queueResponse).json()) as {
        queue_status?: string;
        freshness_assessment?: { requires_refresh?: boolean };
      };

      if (
        queuePayload.queue_status === "blocked" &&
        queuePayload.freshness_assessment?.requires_refresh
      ) {
        await expect(page.getByRole("heading", { name: "Workflow treści bez slopu" })).toBeVisible();
        await expect(page.getByRole("status").getByText(/Następny bezpieczny krok:/)).toBeVisible();
        await page.screenshot({
          path: path.join(runDir, `content-workflow-${viewport.label}-blocked.png`),
          fullPage: true
        });
        continue;
      }

      const context = page.getByLabel("Kontekst zadania treściowego");
      const taskMap = page.getByTestId("content-workflow-task-map");
      readyViewportCount += 1;
      await expect(context).toBeVisible();
      await expect(context.getByText("Strona", { exact: true })).toBeVisible();
      await expect(context.getByText("Usługa", { exact: true })).toBeVisible();
      await expect(context.getByText("Decyzja", { exact: true })).toBeVisible();
      await expect(taskMap.getByRole("button")).toHaveCount(5);
      await expect(taskMap.locator('[aria-current="step"]')).toHaveCount(1);
      await expect(
        taskMap.getByRole("button", { name: /Szkic treści/ })
      ).toHaveAttribute("aria-current", "step");
      await expect(taskMap.getByText("Brakuje zapisanej wersji szkicu")).toBeVisible();
      await expect(taskMap.getByText("Następny bezpieczny krok")).toBeVisible();
      await expect(taskMap.getByRole("button", { name: /Sprawdzenie treści/ })).toBeDisabled();
      await expect(taskMap.getByRole("button", { name: /Szkic na devie/ })).toBeDisabled();

      await expect(page.getByTestId("content-workflow-technical-audit")).toHaveCount(0);
      await expect(page.locator('[data-active-workspace="draft"]')).toBeVisible();
      await expect(page.getByRole("heading", { name: "Tekst sekcji do szkicu" })).toBeVisible();
      await expect(page.getByText("Niezapisany szkic roboczy")).toBeVisible();
      await expect(page.getByRole("heading", { name: "Aktualna strona" })).toHaveCount(0);
      const sectionTabs = page.getByTestId("draft-section-tabs");
      await expect(sectionTabs).toBeVisible();
      expect(await sectionTabs.getByRole("button").count()).toBeGreaterThan(0);
      const sectionTabsOverflow = await sectionTabs.evaluate(
        (element) => element.scrollWidth > element.clientWidth
      );
      expect(sectionTabsOverflow).toBe(false);

      if (viewport.label === "mobile") {
        const safeStepBox = await taskMap.getByTestId("selected-step-safe-next-step").boundingBox();
        expect(safeStepBox).not.toBeNull();
        expect((safeStepBox?.y ?? viewport.height) + (safeStepBox?.height ?? 0)).toBeLessThanOrEqual(
          viewport.height
        );
      }
      await expectNoHorizontalPageOverflow(page);
      await page.screenshot({
        path: path.join(runDir, `content-workflow-${viewport.label}-current-step.png`),
        fullPage: true
      });

      const writesBeforeRevisit = contentWriteRequests.length;
      await taskMap.getByRole("button", { name: /Plan sekcji/ }).click();
      await expect(page.locator('[data-active-workspace="section_map"]')).toBeVisible();
      await expect(page.getByRole("heading", { name: "Aktualna strona" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Sygnały i braki" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Dev draft / ACF" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Tekst sekcji do szkicu" })).toHaveCount(0);
      await expect(
        taskMap.getByRole("button", { name: /Szkic treści/ })
      ).toHaveAttribute("aria-current", "step");
      expect(contentWriteRequests).toHaveLength(writesBeforeRevisit);

      await expectNoHorizontalPageOverflow(page);
      await page.screenshot({
        path: path.join(runDir, `content-workflow-${viewport.label}-revisit.png`),
        fullPage: true
      });
    }

    expect(readyViewportCount).toBe(viewports.length);
    expect(contentWriteRequests).toEqual([]);
  });

  test("synthetic contract proof: wraps exactly five draft tabs at 390px", async ({ page }) => {
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });
    await page.setViewportSize({ width: 390, height: 844 });

    const contentWriteRequests: string[] = [];
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (
        url.pathname.startsWith("/api/content/") &&
        !["GET", "HEAD", "OPTIONS"].includes(request.method())
      ) {
        contentWriteRequests.push(`${request.method()} ${url.pathname}`);
      }
    });

    let expandedTypedSnapshot = false;
    await page.route("**/api/content/work-items/*/snapshot", async (route) => {
      const response = await route.fetch();
      if (response.status() !== 200) {
        await route.fulfill({ response });
        return;
      }

      const snapshot = (await response.json()) as ContentWorkItemWorkflowSnapshotResponse;
      const draft = snapshot.draft_package.draft_package_result.draft_package;
      if (!draft?.sections.length) {
        await route.fulfill({ response });
        return;
      }

      const sourceSections = draft.sections;
      const syntheticHeadings = [
        "Zakres usługi",
        "Problem klienta",
        "Proces współpracy",
        "Dowody i ograniczenia",
        "Następny krok"
      ];
      draft.sections = syntheticHeadings.map((heading, index) => {
        const source = sourceSections[index % sourceSections.length];
        return {
          ...source,
          heading,
          evidence_ids: [...source.evidence_ids],
          draft_notes: [...source.draft_notes]
        };
      });
      draft.section_to_evidence_map = draft.sections.map((section) => ({
        section_heading: section.heading,
        evidence_ids: [...section.evidence_ids]
      }));
      expandedTypedSnapshot = true;
      await route.fulfill({ response, json: snapshot });
    });

    await page.goto("/content-workflow");

    const sectionTabs = page.getByTestId("draft-section-tabs");
    await expect(sectionTabs).toBeVisible();
    await expect(sectionTabs.getByRole("button")).toHaveCount(5);
    expect(expandedTypedSnapshot).toBe(true);
    const sectionTabsOverflow = await sectionTabs.evaluate(
      (element) => element.scrollWidth > element.clientWidth
    );
    expect(sectionTabsOverflow).toBe(false);
    await expectNoHorizontalPageOverflow(page);
    expect(contentWriteRequests).toEqual([]);

    await page.screenshot({
      path: path.join(runDir, "content-workflow-mobile-synthetic-contract-five-tabs.png"),
      fullPage: true
    });
  });
});

async function expectNoHorizontalPageOverflow(page: Page) {
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(hasHorizontalOverflow).toBe(false);
}
