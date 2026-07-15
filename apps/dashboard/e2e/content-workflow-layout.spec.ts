import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

import type {
  ActionObject,
  ContentDraftRevisionBinding,
  ContentDraftRevisionReviewRequest,
  ContentDraftRevisionSaveRequest,
  ContentWorkItemWorkflowSnapshotResponse,
  ContentWordPressDraftActivationPacketResponse
} from "../src/lib/api";

const repoRoot = path.resolve(process.cwd(), "../..");
const proofRoot = process.env.WILQ_DASHBOARD_PROOF_DIR
  ? path.resolve(process.env.WILQ_DASHBOARD_PROOF_DIR)
  : path.join(repoRoot, ".local-lab/proof/dashboard-content-workflow");

const viewports = [
  { label: "desktop", width: 1440, height: 900 },
  { label: "mobile", width: 390, height: 844 }
] as const;

type RevisionProofState = "empty" | "unreviewed" | "approved";
type RevisionWorkspace = ContentWorkItemWorkflowSnapshotResponse["revision_workspace"];
type SavedRevision = NonNullable<RevisionWorkspace["latest_revision"]>;
type SavedRevisionReview = NonNullable<RevisionWorkspace["latest_review"]>;

const revisionProofEvidenceId = "ev_content_revision_browser_proof";

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
      await expect(page.getByText("Szkic nie ma jeszcze zapisanej wersji")).toBeVisible();
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
      const sourceEditorSections = snapshot.revision_workspace.editor_sections;
      if (!sourceEditorSections.length) {
        await route.fulfill({ response });
        return;
      }
      const syntheticEditorSections = syntheticHeadings.map((heading, index) => {
        const source = sourceEditorSections[index % sourceEditorSections.length];
        return {
          ...source,
          heading,
          evidence_ids: [...source.evidence_ids]
        };
      });
      snapshot.revision_workspace.editor_sections = syntheticEditorSections;
      if (snapshot.revision_workspace.latest_revision) {
        snapshot.revision_workspace.latest_revision.sections = syntheticEditorSections;
      }
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

  test("synthetic revision proof: save, reopen, exact review and inline draft wizard", async ({
    page
  }) => {
    test.setTimeout(90_000);
    const runDir = path.join(proofRoot, new Date().toISOString().replace(/[:.]/g, "-"));
    await fs.mkdir(runDir, { recursive: true });

    let baseSnapshot: ContentWorkItemWorkflowSnapshotResponse | null = null;
    let proofState: RevisionProofState = "empty";
    let savedRevision: SavedRevision | null = null;
    let savedReview: SavedRevisionReview | null = null;
    let currentViewportLabel = "desktop";
    const saveRequests: ContentDraftRevisionSaveRequest[] = [];
    const reviewRequests: ContentDraftRevisionReviewRequest[] = [];
    const postRequests: string[] = [];
    const actionStageRequests: Array<{
      viewport: string;
      stage: string;
      payload: Record<string, unknown>;
    }> = [];
    let actionAuditEvents: ActionObject["audit_events"] = [];
    let actionEventSequence = 0;
    let syntheticApplyCompleted = false;

    page.on("request", (request) => {
      if (request.method() !== "POST") return;
      const url = new URL(request.url());
      postRequests.push(`${request.method()} ${url.pathname}`);
    });

    await page.route("**/api/content/work-items/*/snapshot", async (route) => {
      const response = await route.fetch();
      if (response.status() !== 200) {
        await route.fulfill({ response });
        return;
      }
      baseSnapshot ??= (await response.json()) as ContentWorkItemWorkflowSnapshotResponse;
      const snapshot = revisionProofSnapshot(
        baseSnapshot,
        proofState,
        savedRevision,
        savedReview
      );
      await route.fulfill({ response, json: snapshot });
    });

    await page.route(
      /\/api\/content\/work-items\/[^/]+\/draft-revisions(?:\/[^/]+\/review)?$/,
      async (route) => {
        const request = route.request();
        if (request.method() === "OPTIONS") {
          await route.continue();
          return;
        }
        if (request.method() !== "POST" || baseSnapshot === null) {
          await route.fulfill({ status: 405, body: "Method not allowed" });
          return;
        }

        const requestUrl = new URL(request.url());
        const workItemId = decodeURIComponent(requestUrl.pathname.split("/")[4] ?? "");
        if (requestUrl.pathname.endsWith("/review")) {
          const payload = request.postDataJSON() as ContentDraftRevisionReviewRequest;
          reviewRequests.push(payload);
          if (savedRevision === null) {
            await route.fulfill({ status: 409, body: "Missing synthetic revision" });
            return;
          }
          savedReview = {
            decision_id: `content_revision_decision_${currentViewportLabel}_1`,
            decision_number: 1,
            work_item_id: workItemId,
            revision_id: savedRevision.revision_id,
            revision_digest: savedRevision.content_digest,
            reviewed_by: payload.reviewed_by,
            decision: payload.decision,
            notes: payload.notes,
            checked_items: [...payload.checked_items],
            evidence_ids: [...payload.evidence_ids],
            created_at: "2026-07-14T08:05:00Z"
          };
          proofState = "approved";
          const workspace = revisionProofWorkspace(
            baseSnapshot,
            proofState,
            savedRevision,
            savedReview
          );
          await route.fulfill({
            status: 200,
            headers: {
              "access-control-allow-origin": "*",
              "content-type": "application/json"
            },
            json: { status: "recorded", review: savedReview, workspace }
          });
          return;
        }

        const payload = request.postDataJSON() as ContentDraftRevisionSaveRequest;
        saveRequests.push(payload);
        const draftPackage = baseSnapshot.draft_package.draft_package_result.draft_package;
        savedRevision = {
          revision_id: `content_revision_browser_${currentViewportLabel}_1`,
          work_item_id: workItemId,
          revision_number: 1,
          base_revision_id: payload.base_revision_id,
          content_digest: (currentViewportLabel === "desktop" ? "b" : "c").repeat(64),
          draft_package_id: draftPackage?.id ?? "draft_package_browser_proof",
          draft_package_digest: "d".repeat(64),
          final_canonical_url:
            baseSnapshot.preflight.item.final_canonical_url ??
            baseSnapshot.preflight.item.intended_final_url ??
            "https://ekologus.pl/browser-proof/",
          title: payload.title,
          sections: payload.sections.map((section) => ({
            ...section,
            evidence_ids: [...section.evidence_ids]
          })),
          publish_ready: false,
          created_by: payload.created_by,
          created_at: "2026-07-14T08:00:00Z"
        };
        proofState = "unreviewed";
        const workspace = revisionProofWorkspace(
          baseSnapshot,
          proofState,
          savedRevision,
          null
        );
        await route.fulfill({
          status: 200,
          headers: {
            "access-control-allow-origin": "*",
            "content-type": "application/json"
          },
          json: { status: "created", revision: savedRevision, workspace }
        });
      }
    );

    await page.route(
      /\/api\/actions\/act_apply_wordpress_draft_handoff(?:\/(?:validate|preview|review|confirm|impact-check|apply))?$/,
      async (route) => {
        const request = route.request();
        if (request.method() === "OPTIONS") {
          await route.continue();
          return;
        }
        const requestUrl = new URL(request.url());
        if (request.method() === "GET") {
          await route.fulfill({
            status: 200,
            headers: proofResponseHeaders(),
            json: {
              id: "act_apply_wordpress_draft_handoff",
              title: "Utwórz szkic WordPress",
              domain: "wordpress",
              connector: "wordpress_ekologus",
              mode: "apply",
              risk: "high",
              status: "ready",
              evidence_ids: [revisionProofEvidenceId],
              metrics: [],
              human_diagnosis: "Dokładna wersja wymaga kontrolowanego handoffu.",
              recommended_reason: "Utwórz wyłącznie nowy szkic.",
              validation_status: "valid",
              payload: {
                action_type: "wordpress_draft_handoff",
                allowed_operation: "create_wordpress_draft"
              },
              audit_events: actionAuditEvents
            }
          });
          return;
        }
        if (request.method() !== "POST") {
          await route.fulfill({ status: 405, body: "Method not allowed" });
          return;
        }
        const stage = requestUrl.pathname.split("/").at(-1) ?? "";
        const payload = (request.postDataJSON() ?? {}) as Record<string, unknown>;
        actionStageRequests.push({ viewport: currentViewportLabel, stage, payload });
        const binding =
          savedRevision && savedReview
            ? revisionProofBinding(savedRevision, savedReview)
            : null;
        if (stage === "validate") {
          await route.fulfill({
            status: 200,
            headers: proofResponseHeaders(),
            json: {
              action_id: "act_apply_wordpress_draft_handoff",
              valid: true,
              status: "valid",
              errors: [],
              warnings: [],
              checked_at: "2026-07-15T10:00:00Z"
            }
          });
          return;
        }
        if (!binding) {
          await route.fulfill({ status: 409, body: "Missing synthetic revision binding" });
          return;
        }
        const eventTypeByStage: Record<string, string> = {
          preview: "action_preview_generated",
          review: "human_review_approved_for_prepare",
          confirm: "action_apply_confirmed",
          "impact-check": "action_impact_check_completed",
          apply: "action_apply_completed"
        };
        const eventType = eventTypeByStage[stage];
        if (!eventType) {
          await route.fulfill({ status: 404, body: "Unknown synthetic action stage" });
          return;
        }
        actionEventSequence += 1;
        const auditEvent: ActionObject["audit_events"][number] = {
          id: `audit_browser_${currentViewportLabel}_${actionEventSequence}`,
          action_id: "act_apply_wordpress_draft_handoff",
          event_type: eventType,
          event_type_label: eventType,
          actor: "operator_local_dashboard",
          created_at: `2026-07-15T10:00:0${actionEventSequence}Z`,
          summary: eventType,
          evidence_ids: [revisionProofEvidenceId],
          details: { wordpress_draft_binding: binding },
          redacted: true
        };
        actionAuditEvents = [...actionAuditEvents, auditEvent];
        const common = {
          action_id: "act_apply_wordpress_draft_handoff",
          audit_event: auditEvent,
          review_gate: {}
        };
        if (stage === "preview") {
          await route.fulfill({
            status: 200,
            headers: proofResponseHeaders(),
            json: {
              ...common,
              status: "preview_ready",
              dry_run: true,
              mutation_allowed: false,
              preview_items: [],
              preview_items_total: 0,
              omitted_items: 0,
              blockers: []
            }
          });
          return;
        }
        if (stage === "review") {
          await route.fulfill({
            status: 200,
            headers: proofResponseHeaders(),
            json: { ...common, status: "recorded" }
          });
          return;
        }
        if (stage === "confirm") {
          await route.fulfill({
            status: 200,
            headers: proofResponseHeaders(),
            json: { ...common, confirmed: true, status: "confirmed", blockers: [] }
          });
          return;
        }
        if (stage === "impact-check") {
          await route.fulfill({
            status: 200,
            headers: proofResponseHeaders(),
            json: {
              ...common,
              status: "checked",
              pre_window_days: 7,
              post_window_days: 7,
              metric_fact_count: 0,
              source_connectors: ["wordpress_ekologus"],
              evidence_ids: [revisionProofEvidenceId],
              blockers: []
            }
          });
          return;
        }
        syntheticApplyCompleted = true;
        await route.fulfill({
          status: 200,
          headers: proofResponseHeaders(),
          json: {
            action_id: "act_apply_wordpress_draft_handoff",
            applied: true,
            status: "applied",
            audit_event: auditEvent,
            mutation_audit: {
              id: `mutation_audit_browser_${currentViewportLabel}`,
              action_id: "act_apply_wordpress_draft_handoff",
              connector: "wordpress_ekologus",
              action_type: "wordpress_draft_handoff",
              status: "applied",
              adapter_reached: true,
              external_write_attempted: true,
              mutation_attempted: true,
              mutation_adapter: "synthetic_browser_interceptor",
              actor: "operator_local_dashboard",
              created_at: auditEvent.created_at,
              audit_event_id: auditEvent.id,
              evidence_ids: [revisionProofEvidenceId],
              blockers: [],
              wordpress_draft_binding: binding,
              wordpress_revision_blockers: [],
              summary: "Syntetyczny draft utworzony bez połączenia z WordPressem.",
              redacted: true
            },
            errors: [],
            wordpress_revision_blockers: [],
            adapter_result: { wordpress_post_id: `browser-${currentViewportLabel}-1` }
          }
        });
      }
    );

    await page.route("**/api/content/wordpress/draft-activation-packet**", async (route) => {
      const response = await route.fetch();
      if (response.status() !== 200) {
        await route.fulfill({ response });
        return;
      }
      const packet = (await response.json()) as ContentWordPressDraftActivationPacketResponse;
      if (proofState === "approved" && savedRevision && savedReview) {
        const binding = revisionProofBinding(savedRevision, savedReview);
        packet.action_id = "act_apply_wordpress_draft_handoff";
        packet.work_item_id = savedRevision.work_item_id;
        packet.handoff_ready = true;
        packet.handoff_id = binding.handoff_id;
        packet.handoff_blockers = [];
        packet.activation_missing_step = "ready";
        packet.activation_missing_step_label = "gotowe do kontrolowanego zapisu";
        packet.operator_next_step = "Przejdź przez kontrolowany wizard dokładnej wersji.";
        if (syntheticApplyCompleted) {
          packet.draft_readback = {
            status: "available",
            connector: "wordpress_ekologus",
            wordpress_post_id: `browser-${currentViewportLabel}-1`,
            post_status: "draft",
            title: savedRevision.title,
            link: `https://ekologus.dev.proudsite.pl/browser-${currentViewportLabel}-1/`,
            modified_gmt: "2026-07-15T10:00:06Z",
            content_summary: "Syntetyczny readback dokładnej wersji.",
            content_word_count: 42,
            acf_field_count: 0,
            acf_field_names: [],
            blockers: []
          };
        }
      }
      await route.fulfill({ response, json: packet });
    });

    for (const viewport of viewports) {
      currentViewportLabel = viewport.label;
      proofState = "empty";
      savedRevision = null;
      savedReview = null;
      actionAuditEvents = [];
      actionEventSequence = 0;
      syntheticApplyCompleted = false;
      const saveCountBefore = saveRequests.length;
      const reviewCountBefore = reviewRequests.length;
      const postCountBefore = postRequests.length;
      const actionCountBefore = actionStageRequests.length;
      const exactText = `Dokładna treść wersji do review — ${viewport.label}.`;

      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto("/content-workflow");

      const taskMap = page.getByTestId("content-workflow-task-map");
      await expect(taskMap.getByRole("button", { name: /Szkic treści/ })).toHaveAttribute(
        "aria-current",
        "step"
      );
      await expect(page.getByText("Szkic nie ma jeszcze zapisanej wersji")).toBeVisible();
      const sectionEditor = page.locator('textarea[aria-label^="Tekst sekcji "]').first();
      await expect(sectionEditor).toBeVisible();
      await sectionEditor.fill(exactText);
      await page.getByRole("button", { name: "Zapisz wersję do review" }).click();

      await expect.poll(() => saveRequests.length).toBe(saveCountBefore + 1);
      await expect(taskMap.getByRole("button", { name: /Sprawdzenie treści/ })).toHaveAttribute(
        "aria-current",
        "step"
      );
      expect(saveRequests.at(-1)?.base_revision_id).toBeNull();
      expect(saveRequests.at(-1)?.sections[0]?.body_markdown).toBe(exactText);
      expect(saveRequests.at(-1)?.created_by).toBe("wilku");

      await taskMap.getByRole("button", { name: /Szkic treści/ }).click();
      await expect(page.locator('[data-active-workspace="draft"]')).toBeVisible();
      await expect(page.locator('textarea[aria-label^="Tekst sekcji "]').first()).toHaveValue(
        exactText
      );

      await page.reload();
      const reloadedTaskMap = page.getByTestId("content-workflow-task-map");
      await expect(
        reloadedTaskMap.getByRole("button", { name: /Sprawdzenie treści/ })
      ).toHaveAttribute("aria-current", "step");
      await reloadedTaskMap.getByRole("button", { name: /Szkic treści/ }).click();
      await expect(page.locator('textarea[aria-label^="Tekst sekcji "]').first()).toHaveValue(
        exactText
      );
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: path.join(runDir, `content-workflow-${viewport.label}-revision-rehydrated.png`),
        fullPage: true
      });

      await reloadedTaskMap.getByRole("button", { name: /Sprawdzenie treści/ }).click();
      const immutableRevision = page.getByTestId("immutable-revision-content");
      await expect(immutableRevision.getByText(exactText)).toBeVisible();
      await expect(immutableRevision.getByText(revisionProofEvidenceId).first()).toBeVisible();
      await page.getByLabel("Decyzja dla wersji szkicu").selectOption("approved");
      const approveButton = page.getByRole("button", { name: /Zapisz decyzję dla wersji 1/ });
      await expect(approveButton).toBeDisabled();
      await page
        .getByRole("checkbox", { name: "Przeczytano dokładną treść tej wersji." })
        .check();
      await expect(approveButton).toBeDisabled();
      await page
        .getByRole("checkbox", { name: "Sprawdzono dowody przypisane do tej wersji." })
        .check();
      await expect(approveButton).toBeEnabled();
      await approveButton.click();

      await expect(reloadedTaskMap.getByRole("button", { name: /Szkic na devie/ })).toHaveAttribute(
        "aria-current",
        "step"
      );
      const wizard = page.getByTestId("content-wordpress-draft-action-wizard");
      await expect(wizard.getByRole("heading", { name: "Wersja 1 → szkic na devie" }))
        .toBeVisible();
      await expect(wizard.getByText(/bez publikacji · bez aktualizacji/)).toBeVisible();
      await expect.poll(() => reviewRequests.length).toBe(reviewCountBefore + 1);
      expect(reviewRequests.at(-1)?.expected_revision_digest).toBe(
        (currentViewportLabel === "desktop" ? "b" : "c").repeat(64)
      );
      expect(reviewRequests.at(-1)?.decision).toBe("approved");
      expect(reviewRequests.at(-1)?.checked_items).toEqual([
        "Przeczytano dokładną treść tej wersji.",
        "Sprawdzono dowody przypisane do tej wersji."
      ]);
      expect(reviewRequests.at(-1)?.evidence_ids).toContain(revisionProofEvidenceId);

      await wizard.getByRole("button", { name: "Sprawdź wersję i podgląd" }).click();
      const actionReviewCheckbox = wizard.getByRole("checkbox", {
        name: /Sprawdziłem podgląd tej wersji/
      });
      await expect(actionReviewCheckbox).toBeVisible();
      await actionReviewCheckbox.check();
      await wizard.getByRole("button", { name: "Zapisz review akcji" }).click();
      const actionConfirmCheckbox = wizard.getByRole("checkbox", {
        name: /Potwierdzam zamiar utworzenia wyłącznie draftu/
      });
      await expect(actionConfirmCheckbox).toBeVisible();
      await actionConfirmCheckbox.check();
      await wizard.getByRole("button", { name: "Potwierdź draft-only" }).click();
      await wizard.getByRole("button", { name: "Sprawdź gotowość zapisu" }).click();
      await wizard.getByRole("button", { name: "Utwórz szkic na devie" }).click();

      await expect(wizard.getByText("Nowy szkic został zapisany jako draft")).toBeVisible();
      await expect(
        wizard.getByRole("link", { name: "Otwórz odczytany szkic na devie" })
      ).toHaveAttribute(
        "href",
        `https://ekologus.dev.proudsite.pl/browser-${currentViewportLabel}-1/`
      );
      const actionRequestsForViewport = actionStageRequests.slice(actionCountBefore);
      expect(actionRequestsForViewport.map((request) => request.stage)).toEqual([
        "validate",
        "preview",
        "review",
        "confirm",
        "impact-check",
        "apply"
      ]);
      const expectedBinding = revisionProofBinding(savedRevision, savedReview);
      for (const request of actionRequestsForViewport.filter(
        (candidate) => candidate.stage !== "validate"
      )) {
        expect(request.payload.wordpress_draft).toEqual(expectedBinding);
      }
      await expectNoHorizontalPageOverflow(page);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({
        path: path.join(runDir, `content-workflow-${viewport.label}-inline-draft-complete.png`),
        fullPage: true
      });

      expect(postRequests.slice(postCountBefore)).toEqual([
        expect.stringMatching(/^POST \/api\/content\/work-items\/[^/]+\/draft-revisions$/),
        expect.stringMatching(
          /^POST \/api\/content\/work-items\/[^/]+\/draft-revisions\/[^/]+\/review$/
        ),
        "POST /api/actions/act_apply_wordpress_draft_handoff/validate",
        "POST /api/actions/act_apply_wordpress_draft_handoff/preview",
        "POST /api/actions/act_apply_wordpress_draft_handoff/review",
        "POST /api/actions/act_apply_wordpress_draft_handoff/confirm",
        "POST /api/actions/act_apply_wordpress_draft_handoff/impact-check",
        "POST /api/actions/act_apply_wordpress_draft_handoff/apply"
      ]);
    }

    const forbiddenPostRequests = postRequests.filter((entry) =>
      /\/api\/(?:codex(?:\/|$)|content\/[^ ]*wordpress)/i.test(entry)
    );
    expect(forbiddenPostRequests).toEqual([]);
    expect(postRequests).toHaveLength(viewports.length * 8);
  });
});

function revisionProofSnapshot(
  source: ContentWorkItemWorkflowSnapshotResponse,
  state: RevisionProofState,
  revision: SavedRevision | null,
  review: SavedRevisionReview | null
): ContentWorkItemWorkflowSnapshotResponse {
  const snapshot = cloneValue(source);
  snapshot.revision_workspace = revisionProofWorkspace(snapshot, state, revision, review);
  snapshot.current_step_id =
    state === "empty" ? "draft" : state === "unreviewed" ? "review" : "dev_draft";
  const currentStepIndex = snapshot.operator_steps.findIndex(
    (step) => step.id === snapshot.current_step_id
  );
  snapshot.operator_steps = snapshot.operator_steps.map((step, index) => {
    return {
      ...step,
      phase: index < currentStepIndex ? "complete" : index === currentStepIndex ? "current" : "pending",
      can_open: index <= currentStepIndex,
      can_submit:
        (state === "empty" && step.id === "draft") ||
        (state === "unreviewed" && step.id === "review") ||
        (state === "approved" && step.id === "dev_draft")
    };
  });
  const draftStep = snapshot.operator_steps.find((step) => step.id === "draft");
  const reviewStep = snapshot.operator_steps.find((step) => step.id === "review");
  const devDraftStep = snapshot.operator_steps.find((step) => step.id === "dev_draft");
  if (draftStep) {
    draftStep.readiness = state === "empty" ? "review_required" : "ready";
    draftStep.status_label =
      state === "empty" ? "pierwsza wersja wymaga zapisu" : "wersja zapisana do sprawdzenia";
    draftStep.blocker =
      state === "empty"
        ? proofBlocker(
            "missing_revision_bound_draft",
            "Brakuje zapisanej wersji szkicu",
            "Zapisz dokładny tekst, aby późniejsza decyzja dotyczyła tej wersji."
          )
        : null;
  }
  if (reviewStep && state !== "empty") {
    reviewStep.readiness = state === "approved" ? "ready" : "review_required";
    reviewStep.status_label =
      state === "approved" ? "wersja zatwierdzona" : "wersja czeka na sprawdzenie";
    reviewStep.blocker =
      state === "unreviewed"
        ? proofBlocker(
            "missing_revision_review",
            "Wersja czeka na decyzję",
            "Ta zapisana wersja nie ma jeszcze decyzji człowieka."
          )
        : null;
  }
  if (devDraftStep) {
    devDraftStep.readiness = state === "approved" ? "ready" : "blocked";
    devDraftStep.status_label =
      state === "approved"
        ? "zatwierdzona wersja czeka na bezpieczne przekazanie"
        : "czeka na sprawdzenie wersji";
    if (state === "approved") {
      devDraftStep.blocker = null;
      devDraftStep.safe_next_step =
        "Przejdź przez podgląd, review, potwierdzenie i kontrolę tej samej wersji.";
    }
  }
  if (state === "approved" && revision && review) {
    const binding = revisionProofBinding(revision, review);
    snapshot.wordpress_handoff = {
      item: snapshot.wordpress_handoff.item,
      handoff_result: {
        handoff: {
          id: binding.handoff_id,
          work_item_id: revision.work_item_id,
          draft_package_id: revision.draft_package_id,
          human_review_id: review.decision_id,
          audit_id: `audit_browser_handoff_${revision.revision_id}`,
          connector: "wordpress_ekologus",
          operation_type: "create_wordpress_draft",
          status: "prepared",
          post_status: "draft",
          title: revision.title,
          final_canonical_url: revision.final_canonical_url,
          intended_final_url: revision.final_canonical_url,
          preview_url: `https://ekologus.dev.proudsite.pl/${revision.revision_id}/`,
          evidence_ids: [...new Set(revision.sections.flatMap((section) => section.evidence_ids))],
          revision_binding: binding,
          revision_sections: cloneValue(revision.sections),
          publish_allowed: false,
          destructive_update_allowed: false
        },
        blockers: []
      }
    };
  }
  return snapshot;
}

function proofBlocker(code: string, label: string, reason: string) {
  return { code, label, reason };
}

function revisionProofWorkspace(
  source: ContentWorkItemWorkflowSnapshotResponse,
  state: RevisionProofState,
  revision: SavedRevision | null,
  review: SavedRevisionReview | null
): RevisionWorkspace {
  if (state === "empty" || revision === null) {
    const sourceSections = source.revision_workspace.editor_sections.length
      ? source.revision_workspace.editor_sections
      : (source.draft_package.draft_package_result.draft_package?.sections ?? []).map((section) => ({
          heading: section.heading,
          body_markdown: [section.purpose, ...section.draft_notes].join("\n\n"),
          evidence_ids: [...section.evidence_ids]
        }));
    const editorSections = sourceSections.map((section, index) => ({
      ...section,
      evidence_ids:
        index === 0
          ? [...new Set([...section.evidence_ids, revisionProofEvidenceId])]
          : [...section.evidence_ids]
    }));
    return {
      status: "empty",
      latest_revision: null,
      latest_review: null,
      revision_count: 0,
      context_current: true,
      editor_title:
        source.revision_workspace.editor_title ||
        source.draft_package.draft_package_result.draft_package?.title ||
        "Szkic treści",
      editor_sections: editorSections,
      can_save: true,
      can_review: false,
      safe_next_step: "Edytuj tekst i zapisz pierwszą wersję do review."
    };
  }
  return {
    status: state,
    latest_revision: cloneValue(revision),
    latest_review: review ? cloneValue(review) : null,
    revision_count: revision.revision_number,
    context_current: true,
    editor_title: revision.title,
    editor_sections: cloneValue(revision.sections),
    can_save: false,
    can_review: state === "unreviewed",
    safe_next_step:
      state === "unreviewed"
        ? `Sprawdź dokładną treść wersji ${revision.revision_number}.`
        : "Przejdź do kontrolowanego zapisu tej dokładnej wersji jako nowy draft."
  };
}

function revisionProofBinding(
  revision: SavedRevision,
  review: SavedRevisionReview
): ContentDraftRevisionBinding {
  return {
    work_item_id: revision.work_item_id,
    handoff_id: `wordpress_draft_handoff_${revision.revision_id}`,
    revision_id: revision.revision_id,
    content_digest: revision.content_digest,
    draft_package_id: revision.draft_package_id,
    draft_package_digest: revision.draft_package_digest,
    approval_decision_id: review.decision_id,
    final_canonical_url: revision.final_canonical_url
  };
}

function proofResponseHeaders() {
  return {
    "access-control-allow-origin": "*",
    "content-type": "application/json"
  };
}

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

async function expectNoHorizontalPageOverflow(page: Page) {
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(hasHorizontalOverflow).toBe(false);
}
