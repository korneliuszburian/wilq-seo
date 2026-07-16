import { afterEach, describe, expect, it, vi } from "vitest";
import type { ContentWorkItem } from "@wilq/shared-schemas";

import {
  actionApiPath,
  applyAction,
  getActionMutationReadiness,
  getActionsMutationReadiness,
  getContentKnowledgeCards,
  getContentWorkItemEnrichment,
  getContentWorkItemQueue,
  getContentWorkItemSnapshot,
  postContentWorkItemDraftPackage,
  postContentWorkItemCodexSectionProposal,
  postContentWorkItemHumanReview,
  postContentWorkItemMeasurementWindow,
  postContentWorkItemPreflight,
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemSalesBrief,
  postContentWorkItemWordPressDraftExecution,
  postContentWorkItemWordPressDraftHandoff,
  previewAction,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview
} from "./api";

const responseByPath: Record<string, unknown> = {
  "/api/content/knowledge-cards": contentKnowledgeCardsResponse(),
  "/api/content/work-items/queue": contentQueueResponse(),
  "/api/content/work-items/content_work_item_bdo/enrichment": opportunityEnrichmentResponse(),
  "/api/content/work-items/preflight": {
    item: workItem(),
    inventory_resolution: inventoryResolution(),
    preflight_verdict: preflightVerdict("plan_allowed")
  },
  "/api/content/work-items/sales-brief": {
    item: workItem(),
    inventory_resolution: inventoryResolution(),
    preflight_verdict: preflightVerdict("brief_allowed"),
    sales_brief_result: { brief: salesBrief(), blockers: [] }
  },
  "/api/content/work-items/draft-package": {
    item: workItem(),
    inventory_resolution: inventoryResolution(),
    preflight_verdict: preflightVerdict("draft_allowed"),
    sales_brief_result: { brief: salesBrief(), blockers: [] },
    draft_package_result: { draft_package: draftPackage(), blockers: [] }
  },
  "/api/content/work-items/quality-review": {
    item: workItem(),
    quality_review: qualityReview()
  },
  "/api/content/work-items/content_work_item_bdo/quality-review": {
    item: workItem(),
    quality_review: qualityReview()
  },
  "/api/content/work-items/revision-plan": {
    item: workItem(),
    revision_plan: revisionPlan()
  },
  "/api/content/work-items/content_work_item_bdo/revision-plan": {
    item: workItem(),
    revision_plan: revisionPlan()
  },
  "/api/content/work-items/human-review": {
    item: workItem(),
    reviewed_item: workItem({ human_review_status: "approved" }),
    review: humanReview(),
    blockers: [],
    wordpress_handoff_allowed: true
  },
  "/api/content/work-items/snapshot/human-review": {
    item: workItem(),
    reviewed_item: workItem({ human_review_status: "approved" }),
    review: humanReview(),
    blockers: [],
    wordpress_handoff_allowed: true
  },
  "/api/content/work-items/content_work_item_bdo/human-review": {
    item: workItem(),
    reviewed_item: workItem({ human_review_status: "approved" }),
    review: humanReview(),
    blockers: [],
    wordpress_handoff_allowed: true
  },
  "/api/content/work-items/snapshot/audit": {
    item: workItem(),
    handoff_result: { handoff: wordpressHandoff(), blockers: [] }
  },
  "/api/content/work-items/content_work_item_bdo/audit": {
    item: workItem(),
    handoff_result: { handoff: wordpressHandoff(), blockers: [] }
  },
  "/api/content/work-items/wordpress-draft-handoff": {
    item: workItem(),
    handoff_result: { handoff: wordpressHandoff(), blockers: [] }
  },
  "/api/content/work-items/wordpress-draft-execution": {
    execution_result: wordpressDraftExecutionResult()
  },
  "/api/content/work-items/measurement-window": {
    item: workItem(),
    updated_item: workItem({
      measurement_window_status: "planned",
      measurement_window_id: "measurement_window_content_work_item_bdo"
    }),
    measurement_window_result: { window: measurementWindow(), blockers: [] },
    outcome_blockers: [
      {
        code: "measurement_window_not_ready",
        label: "Nie wolno jeszcze oceniać efektu",
        reason: "Okno obserwacji jeszcze trwa.",
        next_step: "Wróć po earliest_verdict_date."
      }
    ]
  },
  "/api/actions/act%2Funsafe%3Fx%3D1/mutation-readiness": {
    response_type: "action_mutation_readiness",
    contract: "action_mutation_readiness_v1",
    action_id: "act/unsafe?x=1",
    title: "Test action",
    connector: "google_ads",
    connector_label: "Google Ads",
    mode: "prepare",
    mode_label: "przygotowanie",
    risk: "medium",
    risk_label: "średnie",
    validation_status: "valid",
    review_gate_status: "validated_prepare_only",
    ready_to_request_apply: false,
    vendor_write_possible: false,
    would_attempt_vendor_write: false,
    mutation_adapter: null,
    requirements: [
      {
        code: "mutation_adapter",
        label: "Bezpieczny adapter zapisu istnieje",
        satisfied: false,
        evidence: null
      }
    ],
    blockers: [
      {
        code: "missing_mutation_adapter",
        label: "Brakuje adaptera zapisu",
        reason: "WILQ nie ma jeszcze implementacji vendor write dla tej akcji.",
        next_step: "Najpierw dodaj read-only preview i bezpieczny adapter dry-run/live."
      }
    ],
    operator_next_step: "Najpierw dodaj read-only preview i bezpieczny adapter dry-run/live.",
    evidence_ids: ["ev_connector_google_ads_status"],
    source_connectors: ["google_ads"],
    latest_mutation_audit_id: null,
    latest_mutation_audit_status: null
  },
  "/api/actions/mutation-readiness": {
    response_type: "action_mutation_readiness_summary",
    contract: "action_mutation_readiness_summary_v1",
    action_count: 1,
    ready_to_request_apply_count: 0,
    vendor_write_possible_count: 0,
    would_attempt_vendor_write_count: 0,
    prepare_only_count: 1,
    missing_adapter_count: 1,
    high_risk_blocked_count: 0,
    top_blockers: ["missing_mutation_adapter"],
    first_write_candidate: {
      response_type: "action_mutation_readiness",
      contract: "action_mutation_readiness_v1",
      action_id: "act_prepare_ads_campaign_review_queue",
      title: "Przygotuj kolejkę przeglądu kampanii Google Ads",
      connector: "google_ads",
      connector_label: "Google Ads",
      mode: "prepare",
      mode_label: "przygotowanie",
      risk: "medium",
      risk_label: "średnie",
      validation_status: "valid",
      review_gate_status: "validated_prepare_only",
      ready_to_request_apply: false,
      vendor_write_possible: false,
      would_attempt_vendor_write: false,
      mutation_adapter: null,
      target_candidate_id: null,
      target_label: null,
      target_url: null,
      requirements: [],
      blockers: [],
      operator_next_step: "Użyj jej do review albo dodaj osobny apply-capable ActionObject.",
      evidence_ids: ["ev_connector_google_ads_status"],
      source_connectors: ["google_ads"],
      latest_mutation_audit_id: null,
      latest_mutation_audit_status: null
    },
    first_write_candidate_reason: "Pierwszy kandydat do aktywowania zapisu.",
    activation_plan_steps: [
      "Utrzymaj zakres draft-only i brak publikacji/destrukcyjnych zmian.",
      "Zbuduj osobny apply-capable ActionObject dla tej klasy zapisu."
    ],
    activation_next_step: "Najbliższy krok: przygotuj osobny apply-capable ActionObject.",
    operator_next_step: "Najpierw dodaj read-only preview i bezpieczny adapter dry-run/live.",
    items: [
      {
        response_type: "action_mutation_readiness",
        contract: "action_mutation_readiness_v1",
        action_id: "act_prepare_ads_campaign_review_queue",
        title: "Przygotuj kolejkę przeglądu kampanii Google Ads",
        connector: "google_ads",
        connector_label: "Google Ads",
        mode: "prepare",
        mode_label: "przygotowanie",
        risk: "medium",
        risk_label: "średnie",
        validation_status: "valid",
        review_gate_status: "validated_prepare_only",
        ready_to_request_apply: false,
        vendor_write_possible: false,
        would_attempt_vendor_write: false,
        mutation_adapter: null,
        requirements: [],
        blockers: [],
        operator_next_step: "Użyj jej do review albo dodaj osobny apply-capable ActionObject.",
        evidence_ids: ["ev_connector_google_ads_status"],
        source_connectors: ["google_ads"],
        latest_mutation_audit_id: null,
        latest_mutation_audit_status: null
      }
    ]
  }
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("content workflow API helpers", () => {
  it("encodes action IDs for every action helper path suffix", () => {
    const actionId = "act/unsafe?x=1";

    expect(actionApiPath(actionId)).toBe("/api/actions/act%2Funsafe%3Fx%3D1");
    expect(actionApiPath(actionId, "/validate")).toBe(
      "/api/actions/act%2Funsafe%3Fx%3D1/validate"
    );
    expect(actionApiPath(actionId, "/preview")).toBe(
      "/api/actions/act%2Funsafe%3Fx%3D1/preview"
    );
    expect(actionApiPath(actionId, "/review")).toBe(
      "/api/actions/act%2Funsafe%3Fx%3D1/review"
    );
    expect(actionApiPath(actionId, "/confirm")).toBe(
      "/api/actions/act%2Funsafe%3Fx%3D1/confirm"
    );
    expect(actionApiPath(actionId, "/impact-check")).toBe(
      "/api/actions/act%2Funsafe%3Fx%3D1/impact-check"
    );
    expect(actionApiPath(actionId, "/mutation-readiness")).toBe(
      "/api/actions/act%2Funsafe%3Fx%3D1/mutation-readiness"
    );
  });

  it("gets encoded action mutation readiness through a typed helper", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      const path = new URL(String(url)).pathname;
      return {
        ok: true,
        json: async () => responseByPath[path]
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    const readiness = await getActionMutationReadiness("act/unsafe?x=1");

    expect(readiness.response_type).toBe("action_mutation_readiness");
    expect(readiness.vendor_write_possible).toBe(false);
    expect(readiness.blockers[0]?.code).toBe("missing_mutation_adapter");
    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/actions/act%2Funsafe%3Fx%3D1/mutation-readiness"
    ]);
  });

  it("keeps the exact WordPress binding in preview and parses a typed apply conflict", async () => {
    const binding = {
      work_item_id: "content_work_item_bdo",
      handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
      revision_id: "content_revision_bdo_1",
      content_digest: "a".repeat(64),
      draft_package_id: "draft_package_content_work_item_bdo",
      draft_package_digest: "b".repeat(64),
      planning_digest: "c".repeat(64),
      approval_decision_id: "content_revision_decision_bdo_1",
      final_canonical_url: "https://ekologus.pl/bdo/"
    };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(url)).pathname;
      expect(init?.method).toBe("POST");
      if (path.endsWith("/preview")) {
        expect(JSON.parse(String(init?.body))).toEqual({
          requested_by: "operator_local_dashboard",
          max_items: 8,
          wordpress_draft: binding
        });
        return {
          ok: true,
          status: 200,
          json: async () => ({
            action_id: "act_apply_wordpress_draft_handoff",
            status: "preview_ready",
            dry_run: true,
            mutation_allowed: false,
            preview_items: [],
            preview_items_total: 0,
            omitted_items: 0,
            blockers: [],
            audit_event: {
              id: "audit_preview_exact_revision",
              action_id: "act_apply_wordpress_draft_handoff",
              event_type: "action_preview_generated",
              actor: "operator_local_dashboard",
              summary: "Podgląd dokładnej wersji.",
              created_at: "2026-07-11T00:00:00Z",
              evidence_ids: [],
              details: { wordpress_draft_binding: binding },
              redacted: true
            },
            review_gate: {}
          })
        } as Response;
      }
      expect(path).toBe("/api/actions/act_apply_wordpress_draft_handoff/apply");
      expect(JSON.parse(String(init?.body))).toEqual({
        confirm: true,
        confirmed_by: "operator_local_dashboard",
        wordpress_draft: binding
      });
      const blocker = {
        code: "wordpress_revision_binding_mismatch",
        label: "Wersja szkicu zmieniła się",
        reason: "Binding nie wskazuje aktualnie zaakceptowanej wersji.",
        next_step: "Wróć do review aktualnej wersji."
      };
      return {
        ok: false,
        status: 409,
        json: async () => ({
          detail: {
            action_id: "act_apply_wordpress_draft_handoff",
            applied: false,
            status: "blocked",
            audit_event: {
              id: "audit_apply_blocked",
              action_id: "act_apply_wordpress_draft_handoff",
              event_type: "action_apply_blocked",
              actor: "operator_local_dashboard",
              summary: "Apply zablokowany przed zapisem.",
              created_at: "2026-07-11T00:00:01Z",
              evidence_ids: [],
              details: {
                wordpress_draft_binding: binding,
                wordpress_revision_blockers: [blocker]
              },
              redacted: true
            },
            mutation_audit: {
              id: "mutation_audit_blocked",
              action_id: "act_apply_wordpress_draft_handoff",
              connector: "wordpress_ekologus",
              mutation_adapter: "wordpress_draft_execution_boundary",
              status: "blocked",
              summary: "Blokada przed adapterem.",
              mutation_attempted: false,
              adapter_reached: false,
              external_write_attempted: false,
              actor: "operator_local_dashboard",
              created_at: "2026-07-11T00:00:01Z",
              audit_event_id: "audit_apply_blocked",
              evidence_ids: [],
              blockers: [blocker.code],
              wordpress_draft_binding: binding,
              wordpress_revision_blockers: [blocker],
              redacted: true
            },
            errors: [blocker.reason],
            wordpress_revision_blockers: [blocker]
          },
        })
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await previewAction("act_apply_wordpress_draft_handoff", {
      requested_by: "operator_local_dashboard",
      max_items: 8,
      wordpress_draft: binding
    });
    const result = await applyAction("act_apply_wordpress_draft_handoff", {
      confirm: true,
      confirmed_by: "operator_local_dashboard",
      wordpress_draft: binding
    });

    expect(result.status).toBe("blocked");
    expect(result.wordpress_revision_blockers[0]?.code).toBe(
      "wordpress_revision_binding_mismatch"
    );
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("gets the action mutation readiness summary through a typed helper", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      const path = new URL(String(url)).pathname;
      return {
        ok: true,
        json: async () => responseByPath[path]
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    const readiness = await getActionsMutationReadiness();

    expect(readiness.response_type).toBe("action_mutation_readiness_summary");
    expect(readiness.vendor_write_possible_count).toBe(0);
    expect(readiness.items[0]?.action_id).toBe("act_prepare_ads_campaign_review_queue");
    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/actions/mutation-readiness"
    ]);
  });

  it("gets the API-owned diagnostics-derived snapshot for the content workflow route", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      const path = new URL(String(url)).pathname;
      return {
        ok: true,
        json: async () =>
          path === "/api/content/work-items/snapshot"
            ? workflowSnapshot()
            : responseByPath[path]
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    const snapshot = await getContentWorkItemSnapshot();

    expect(snapshot.response_type).toBe("workflow_snapshot");
    if (snapshot.response_type !== "workflow_snapshot") throw new Error("Expected workflow snapshot");
    expect(snapshot.preflight.item.id).toBe("content_work_item_bdo");
    expect(snapshot.service_profile_context.service_card_id).toBe(
      "ekologus_service_bdo_reporting"
    );
    expect(snapshot.service_profile_context.decision_status).toBe("blocked");
    expect(snapshot.service_profile_context.evidence_ids).toEqual([
      "ev_content_service_profile_source_facts"
    ]);
    expect(snapshot.service_profile_context.service_candidates[0]?.recommended).toBe(true);
    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/content/work-items/snapshot"
    ]);
  });

  it("saves a child revision and reviews its exact digest through encoded typed paths", async () => {
    const revision = draftRevision();
    const workspace = revisionWorkspaceWithRevision(revision);
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      void init;
      const path = new URL(String(url)).pathname;
      if (path.endsWith("/review")) {
        const review = draftRevisionReview(revision);
        return new Response(
          JSON.stringify({
            status: "recorded",
            review,
            workspace: {
              ...workspace,
              status: "approved",
              latest_review: review,
              can_review: false
            }
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(JSON.stringify({ status: "created", revision, workspace }), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const sections = revision.sections;
    const saved = await saveContentWorkItemDraftRevision(
      {
        base_revision_id: "content_revision_bdo_1",
        title: revision.title,
        sections,
        created_by: "wilku"
      },
      "content/work item"
    );
    const reviewed = await saveContentWorkItemDraftRevisionReview(
      {
        expected_revision_digest: revision.content_digest,
        reviewed_by: "wilku",
        decision: "approved",
        notes: "",
        checked_items: ["Sprawdzono dokładną wersję."],
        evidence_ids: ["ev_gsc_bdo"]
      },
      "content/work item",
      "revision/2"
    );

    expect(saved.status).toBe("created");
    expect(reviewed.status).toBe("recorded");
    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/content/work-items/content%2Fwork%20item/draft-revisions",
      "/api/content/work-items/content%2Fwork%20item/draft-revisions/revision%2F2/review"
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      base_revision_id: "content_revision_bdo_1",
      title: revision.title,
      sections: sections.map((section) => ({
        ...section,
        query_terms: [],
        claim_ids: []
      })),
      created_by: "wilku"
    });
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      expected_revision_digest: revision.content_digest,
      reviewed_by: "wilku",
      decision: "approved",
      notes: "",
      checked_items: ["Sprawdzono dokładną wersję."],
      evidence_ids: ["ev_gsc_bdo"]
    });
  });

  it("returns a typed 409 revision conflict without hiding the current version", async () => {
    const conflict = {
      status: "conflict",
      code: "stale_base",
      current_revision_id: "content_revision_bdo_2",
      current_digest: "b".repeat(64),
      safe_next_step: "Porównaj swój tekst z aktualną wersją i scal zmiany ręcznie."
    } as const;
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify(conflict), {
        status: 409,
        headers: { "Content-Type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await saveContentWorkItemDraftRevision(
      {
        base_revision_id: "content_revision_bdo_1",
        title: "BDO dla firm",
        sections: draftRevision().sections,
        created_by: "wilku"
      },
      "content_work_item_bdo"
    );

    expect(result).toEqual(conflict);
  });

  it("posts an exact encoded Codex section proposal and preserves a typed blocker", async () => {
    const blocked = {
      status: "conflict",
      run_id: null,
      work_item_id: "content/work item",
      base_revision_id: "revision/1?stale",
      selected_section_headings: ["Kogo dotyczy BDO"],
      revision: null,
      quality_review: null,
      quality_review_scope: "persisted_selected_sections_and_declared_lineage",
      semantic_review_required: true,
      runtime: {
        status: "not_started",
        thread_id: null,
        turn_id: null,
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      evidence_ids: ["ev_gsc_bdo"],
      source_connectors: ["google_search_console"],
      blockers: [
        {
          code: "stale_base_revision",
          label: "Wersja bazowa nie jest już aktualna",
          reason: "W workspace istnieje nowsza wersja.",
          next_step: "Odśwież workspace i wybierz sekcje aktualnej wersji.",
          source_codes: ["stale_base"]
        }
      ],
      safe_next_step: "Odśwież workspace i wybierz sekcje aktualnej wersji.",
      publish_ready: false
    } as const;
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      void url;
      void init;
      return new Response(JSON.stringify(blocked), {
        status: 409,
        headers: { "Content-Type": "application/json" }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await postContentWorkItemCodexSectionProposal(
      {
        expected_base_digest: "a".repeat(64),
        selected_section_headings: ["Kogo dotyczy BDO"],
        requested_by: "wilku"
      },
      "content/work item",
      "revision/1?stale"
    );

    expect(result).toEqual(blocked);
    expect(new URL(String(fetchMock.mock.calls[0]?.[0])).pathname).toBe(
      "/api/content/work-items/content%2Fwork%20item/draft-revisions/revision%2F1%3Fstale/codex-proposal"
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      expected_base_digest: "a".repeat(64),
      selected_section_headings: ["Kogo dotyczy BDO"],
      requested_by: "wilku"
    });
  });

  it("uses every API-owned Goal 004 content workflow endpoint through typed helpers", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      const path = new URL(String(url)).pathname;
      return {
        ok: true,
        json: async () =>
          path === "/api/content/work-items/content_work_item_bdo/snapshot"
            ? workflowSnapshot()
            : responseByPath[path]
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await getContentWorkItemQueue();
    await getContentKnowledgeCards();
    await getContentWorkItemSnapshot("content_work_item_bdo");
    await getContentWorkItemEnrichment("content_work_item_bdo");
    await postContentWorkItemPreflight({ item: workItem() });
    await postContentWorkItemSalesBrief({
      item: workItem(),
      claim_ledger: claimLedger(),
      seed: salesBriefSeed()
    });
    await postContentWorkItemDraftPackage({
      item: workItem(),
      claim_ledger: claimLedger(),
      seed: salesBriefSeed()
    });
    await postContentWorkItemQualityReview(qualityReviewRequest());
    await postContentWorkItemQualityReview(qualityReviewRequest(), "content_work_item_bdo");
    await postContentWorkItemRevisionPlan({
      item: workItem(),
      quality_review: qualityReview()
    });
    await postContentWorkItemRevisionPlan(
      {
        item: workItem(),
        quality_review: qualityReview()
      },
      "content_work_item_bdo"
    );
    await postContentWorkItemHumanReview({ item: workItem(), review: humanReview() });
    await saveContentWorkItemSnapshotHumanReview({ review: humanReview() });
    await saveContentWorkItemSnapshotHumanReview(
      { review: humanReview() },
      "content_work_item_bdo"
    );
    await saveContentWorkItemSnapshotAudit({
      audit: {
        audit_id: "audit_bdo",
        actor: "wilku",
        reason: "Zatwierdzony szkic może trafić do WordPress jako draft.",
        evidence_ids: ["ev_gsc_bdo"],
        human_review_id: "human_review_bdo"
      }
    });
    await saveContentWorkItemSnapshotAudit(
      {
        audit: {
          audit_id: "audit_bdo",
          actor: "wilku",
          reason: "Zatwierdzony szkic może trafić do WordPress jako draft.",
          evidence_ids: ["ev_gsc_bdo"],
          human_review_id: "human_review_bdo"
        }
      },
      "content_work_item_bdo"
    );
    await postContentWorkItemWordPressDraftHandoff({ item: workItem() });
    await postContentWorkItemWordPressDraftExecution({
      handoff: wordpressHandoff(),
      draft_package: draftPackage(),
      mode: "dry_run"
    });
    await postContentWorkItemMeasurementWindow({
      item: workItem(),
      baseline_period: { start: "2026-05-01", end: "2026-05-31" },
      observation_period: { start: "2026-07-01", end: "2026-07-31" },
      allowed_metrics: ["gsc_clicks"],
      source_connectors: ["google_search_console"]
    });

    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/content/work-items/queue",
      "/api/content/knowledge-cards",
      "/api/content/work-items/content_work_item_bdo/snapshot",
      "/api/content/work-items/content_work_item_bdo/enrichment",
      "/api/content/work-items/preflight",
      "/api/content/work-items/sales-brief",
      "/api/content/work-items/draft-package",
      "/api/content/work-items/quality-review",
      "/api/content/work-items/content_work_item_bdo/quality-review",
      "/api/content/work-items/revision-plan",
      "/api/content/work-items/content_work_item_bdo/revision-plan",
      "/api/content/work-items/human-review",
      "/api/content/work-items/snapshot/human-review",
      "/api/content/work-items/content_work_item_bdo/human-review",
      "/api/content/work-items/snapshot/audit",
      "/api/content/work-items/content_work_item_bdo/audit",
      "/api/content/work-items/wordpress-draft-handoff",
      "/api/content/work-items/wordpress-draft-execution",
      "/api/content/work-items/measurement-window"
    ]);
  });

  it("surfaces API error status and detail for operator debugging", async () => {
    const fetchMock = vi.fn(async () => {
      return {
        ok: false,
        status: 422,
        json: async () => ({ detail: "missing_source_connector" })
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getContentWorkItemQueue()).rejects.toThrow(
      "API request failed: /api/content/work-items/queue (422): missing_source_connector"
    );
  });

  it("validates content workflow request bodies before calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    expect(() =>
      postContentWorkItemSalesBrief({
        item: workItem(),
        claim_ledger: {},
        seed: {}
      } as Parameters<typeof postContentWorkItemSalesBrief>[0])
    ).toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function contentKnowledgeCardsResponse() {
  return {
    cards: [
      {
        id: "ekologus_service_environmental_compliance",
        card_type: "service",
        title: "Obsługa środowiskowa i zgodność obowiązków",
        summary: "Ekologus pomaga firmom porządkować obowiązki środowiskowe.",
        service_fit_terms: ["bdo", "odpady", "środowisk"],
        buyer_problem_terms: ["obowiązki", "kontrola"],
        buyer_triggers: ["zbliżający się termin sprawozdawczy"],
        cta_patterns: ["Zaproponuj konsultację obowiązków bez gwarancji wyniku."],
        allowed_claims: ["Ekologus może pomóc firmie uporządkować obowiązki."],
        claims_needing_review: [
          {
            id: "knowledge_claim_environmental_review",
            claim_type: "environmental_claim",
            status: "needs_human_review",
            label: "Twierdzenie środowiskowe wymaga sprawdzenia",
            reason: "Zakres obowiązków zależy od sytuacji firmy.",
            required_evidence_types: ["service_card", "human_review"]
          }
        ],
        forbidden_claims: [],
        evidence_requirements: ["Dowód bieżący z connectora jest wymagany."],
        measurement_sensitive_claims: [],
        source_lineage: ["docs/goals/archive/004-goal.md"],
        confidence: 0.88,
        freshness: "seeded_goal_004",
        usage_notes: ["Karta wiedzy nie zastępuje live evidence."]
      }
    ],
    card_count: 1,
    source_lineage: ["docs/goals/archive/004-goal.md"],
    production_depth_readiness: {
      status: "seeded_contract_proof",
      status_label: "seed proof, nie produkcyjna wiedza",
      ready_for_daily_content: false,
      seeded_card_count: 1,
      source_backed_review_required_count: 0,
      production_depth_card_count: 0,
      blocker_labels: ["Brakuje zatwierdzonych production-depth kart usług Ekologus."]
    }
  };
}

function workflowSnapshot() {
  return {
    response_type: "workflow_snapshot",
    freshness_assessment: contentFreshnessAssessment(),
    candidate: contentQueueResponse().candidates[0],
    service_profile_context: {
      binding_status: "bound",
      decision_status: "blocked",
      status_label: "Kontekst usługi nie jest zatwierdzony do finalnych treści",
      reason: "Service Profile wymaga review.",
      service_card_id: "ekologus_service_bdo_reporting",
      service_label: "BDO i sprawozdawczość środowiskowa",
      service_status: "source_backed_review_required",
      service_status_label: "źródło istnieje, wymagane review",
      service_selection_confirmed: false,
      human_override_review_required: false,
      service_candidates: [
        {
          service_card_id: "ekologus_service_bdo_reporting",
          service_label: "BDO i sprawozdawczość środowiskowa",
          lifecycle_status: "source_backed_review_required",
          lifecycle_label: "źródło wymaga review",
          matched_terms: ["bdo"],
          match_reasons: ["Temat lub adres strony zawiera dokładną frazę „bdo”."],
          recommended: true
        }
      ],
      freshness_label: "publiczna strona wymaga review (ostatni sygnał: 2026-07-02)",
      freshness_as_of: "2026-07-02",
      source_summary_label: "Źródło profilu: publiczna strona Ekologus",
      allowed_claims: ["Ekologus może pomóc firmie uporządkować obowiązki BDO."],
      claims_needing_review: ["Potwierdź zakres usługi przed finalnym draftem"],
      blocked_claims: ["Gwarancje efektu są zablokowane"],
      claim_policy_scope_label:
        "Ten skrót dotyczy tylko dopasowanej karty usługi. Pełny rejestr twierdzeń dla szkicu jest niżej.",
      evidence_requirements: ["Dowód bieżący z connectora jest wymagany."],
      missing_contracts: ["Publiczne karty usług sprawdzone przez człowieka"],
      safe_next_step: "Sprawdź kartę usługi BDO przed finalnym draftem.",
      source_connectors: ["public_site"],
      evidence_ids: ["ev_content_service_profile_source_facts"],
      knowledge_card_ids: ["ekologus_service_bdo_reporting"],
      review_action_id: "service_profile_review_card_ekologus_service_bdo_reporting",
      review_action_label: "Sprawdź kartę usługi: BDO i sprawozdawczość środowiskowa"
    },
    claim_ledger: claimLedger(),
    preflight: responseByPath["/api/content/work-items/preflight"],
    sales_brief: responseByPath["/api/content/work-items/sales-brief"],
    draft_package: responseByPath["/api/content/work-items/draft-package"],
    structured_generation_readiness: {
      status: "ready",
      editable_section_headings: ["Kogo dotyczy BDO"],
      blockers: [],
      safe_next_step: "Wybierz sekcje zapisanej wersji do poprawy z Codexem.",
      publish_ready: false
    },
    human_review: responseByPath["/api/content/work-items/human-review"],
    wordpress_handoff: responseByPath["/api/content/work-items/wordpress-draft-handoff"],
    measurement_window: responseByPath["/api/content/work-items/measurement-window"],
    revision_workspace: revisionWorkspace(),
    current_step_id: "draft",
    operator_steps: workflowOperatorSteps()
  };
}

function revisionWorkspace() {
  const source = draftPackage();
  const editorSections = [
    {
      heading: "Kogo dotyczy BDO",
      body_markdown: "Zakres obowiązków BDO wymaga sprawdzenia.",
      evidence_ids: ["ev_wp_bdo"]
    }
  ];
  return {
    status: "empty",
    latest_revision: null,
    latest_review: null,
    revision_count: 0,
    context_current: true,
    editor_title: source.title,
    editor_sections: editorSections,
    can_save: true,
    can_review: false,
    safe_next_step: "Zapisz pierwszą wersję szkicu."
  };
}

function draftRevision() {
  return {
    revision_id: "content_revision_bdo_2",
    work_item_id: "content_work_item_bdo",
    revision_number: 2,
    base_revision_id: "content_revision_bdo_1",
    content_digest: "b".repeat(64),
    draft_package_id: "draft_package_content_work_item_bdo",
    draft_package_digest: "d".repeat(64),
    planning_digest: "c".repeat(64),
    final_canonical_url: "https://ekologus.pl/bdo/",
    title: "BDO dla firm",
    sections: [
      {
        heading: "Kogo dotyczy BDO",
        body_markdown: "Treść zapisanej drugiej wersji.",
        evidence_ids: ["ev_gsc_bdo"]
      }
    ],
    publish_ready: false as const,
    created_by: "wilku",
    created_at: "2026-07-14T04:00:00Z"
  };
}

function draftRevisionReview(revision: ReturnType<typeof draftRevision>) {
  return {
    decision_id: "content_revision_decision_bdo_1",
    decision_number: 1,
    work_item_id: revision.work_item_id,
    revision_id: revision.revision_id,
    revision_digest: revision.content_digest,
    decision: "approved" as const,
    reviewed_by: "wilku",
    notes: "",
    checked_items: ["Sprawdzono dokładną wersję."],
    evidence_ids: ["ev_gsc_bdo"],
    created_at: "2026-07-14T04:05:00Z"
  };
}

function revisionWorkspaceWithRevision(revision: ReturnType<typeof draftRevision>) {
  return {
    status: "unreviewed" as const,
    latest_revision: revision,
    latest_review: null,
    revision_count: revision.revision_number,
    context_current: true,
    editor_title: revision.title,
    editor_sections: revision.sections,
    can_save: false,
    can_review: true,
    safe_next_step: `Sprawdź wersję ${revision.revision_number}.`
  };
}

function workflowOperatorSteps() {
  return [
    operatorStep("scope", "Zakres i cel", "complete", "ready", true, null),
    operatorStep("section_map", "Plan sekcji", "complete", "ready", true, null),
    operatorStep(
      "draft",
      "Szkic treści",
      "current",
      "review_required",
      true,
      "missing_revision_bound_draft"
    ),
    operatorStep(
      "review",
      "Sprawdzenie treści",
      "pending",
      "blocked",
      false,
      "missing_revision_bound_draft"
    ),
    operatorStep(
      "dev_draft",
      "Szkic na devie",
      "pending",
      "blocked",
      false,
      "missing_revision_bound_review"
    )
  ];
}

function operatorStep(
  id: string,
  title: string,
  phase: string,
  readiness: string,
  canOpen: boolean,
  blockerCode: string | null
) {
  return {
    id,
    title,
    phase,
    readiness,
    status_label: readiness === "ready" ? "gotowe" : "wymaga pracy",
    summary: `${title}: stan API`,
    can_open: canOpen,
    can_submit: false,
    blocker: blockerCode
      ? { code: blockerCode, label: "Brakuje wersji", reason: "Wymagana jest konkretna wersja." }
      : null,
    safe_next_step: "Wykonaj następny bezpieczny krok."
  };
}

function contentQueueResponse() {
  return {
    queue_status: "ready",
    candidate_count: 1,
    actionable_candidate_count: 1,
    minimum_actionable_candidate_count: 1,
    freshness_assessment: contentFreshnessAssessment(),
    operator_summary: "WILQ ma jednego kandydata do pracy nad treścią.",
    candidates: [
      {
        work_item_id: "content_work_item_bdo",
        decision_id: "content_decision_bdo",
        title: "BDO dla firm",
        topic: "BDO dla firm",
        priority: 10,
        recommended_mode: "refresh",
        recommended_mode_label: "Odśwież",
        status_label: "gotowe do pracy",
        reason: "Istniejąca treść ma dowody i finalny adres.",
        evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
        source_connectors: ["google_search_console", "wordpress_ekologus"],
        source_connector_labels: ["Google Search Console", "WordPress"],
        source_public_url: "https://ekologus.pl/bdo/",
        final_canonical_url: "https://ekologus.pl/bdo/",
        intended_final_url: "https://ekologus.pl/bdo/",
        preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
        preflight_status: "draft_allowed",
        preflight_status_label: "można przygotować szkic",
        duplicate_canonical_risk_summary: "Finalny canonical jest publiczny.",
        measurement_readiness: {
          status: "ready_to_plan",
          label: "pomiar gotowy",
          reason: "GSC i GA4 są dostępne.",
          source_connectors: ["google_search_console", "google_analytics_4"]
        },
        safe_next_step: "Otwórz workflow i przygotuj szkic do review.",
        freshness_assessment: contentFreshnessAssessment(),
        blockers: []
      }
    ],
    blockers: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"]
  };
}

function contentFreshnessAssessment() {
  return {
    state: "fresh",
    state_label: "dane treści świeże",
    checked_at: "2026-07-11T08:00:00Z",
    stale_after_hours: 48,
    requires_refresh: false,
    missing_connector_ids: [],
    blocked_connector_ids: [],
    stale_connector_ids: [],
    connector_labels_requiring_refresh: [],
    summary: "Podstawowe dane treści są świeże.",
    next_step: "Można przejść do decyzji contentowej."
  };
}

function opportunityEnrichmentResponse() {
  return {
    enrichment: {
      id: "content_opportunity_enrichment_content_work_item_bdo",
      work_item_id: "content_work_item_bdo",
      decision_id: "content_decision_bdo",
      status: "ready" as const,
      status_label: "gotowe do pracy nad treścią",
      title: "BDO dla firm",
      topic: "BDO dla firm",
      recommended_mode: "refresh" as const,
      recommended_mode_label: "odśwież istniejącą treść",
      intent: "compliance_risk" as const,
      intent_label: "intencja ryzyka lub obowiązku",
      buyer_problem: "Firma chce zrozumieć obowiązki BDO bez ryzyka błędu.",
      buyer_trigger: "obawa przed błędem formalnym, terminem albo kontrolą",
      service_fit: "obsługa środowiskowa i zgodność obowiązków",
      cta_hypothesis: "Zaproponuj konsultację obowiązków bez gwarancji wyniku.",
      source_facts: [
        {
          id: "source_fact_queries_bdo",
          signal_kind: "gsc_query" as const,
          label: "Zapytania GSC",
          summary: "bdo dla firm",
          evidence_ids: ["ev_gsc_bdo"],
          source_connectors: ["google_search_console"],
          metric_value: null,
          source_url: "https://ekologus.pl/bdo/"
        }
      ],
      measurement_baseline: {
        status: "ready_to_plan" as const,
        label: "baza pomiaru do zaplanowania",
        reason: "WILQ może planować pomiar, ale nie może claimować efektu.",
        metrics_to_watch: ["gsc_clicks", "gsc_impressions"],
        evidence_ids: ["ev_gsc_bdo"],
        source_connectors: ["google_search_console"]
      },
      blockers: [],
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      source_connectors: ["google_search_console", "wordpress_ekologus"],
      safe_next_step: "Przygotuj preserve-first brief."
    },
    blockers: []
  };
}

function workItem(overrides: Partial<ContentWorkItem> = {}): ContentWorkItem {
  return {
    id: "content_work_item_bdo",
    topic: "BDO dla firm",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    wordpress_title_or_h1: "BDO dla firm",
    wordpress_section_headings: ["Co to jest BDO", "Kogo dotyczy BDO"],
    wordpress_section_count: 2,
    wordpress_section_inventory_status: "available",
    wordpress_content_inventory_status: "available",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    inventory_status: "resolved",
    canonical_status: "resolved",
    duplicate_status: "checked",
    preflight_status: "handoff_allowed",
    preserve_first_plan_status: "approved",
    sales_brief_status: "approved",
    sales_brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_status: "approved",
    claim_ledger_id: "claim_ledger_bdo",
    draft_package_status: "ready",
    draft_package_id: "draft_package_content_work_item_bdo",
    human_review_status: "missing",
    human_review_id: null,
    wordpress_handoff_status: "missing",
    wordpress_post_id: null,
    measurement_window_status: "planned",
    measurement_window_id: "measurement_window_content_work_item_bdo",
    audit_status: "missing",
    audit_id: null,
    ...overrides
  };
}

function qualityReviewRequest() {
  return {
    item: workItem(),
    sales_brief: salesBrief(),
    draft_package: draftPackage(),
    claim_ledger: claimLedger(),
    structured_output: structuredDraftOutput(),
    duplicate_risk: "clear" as const
  };
}

function claimLedger() {
  return {
    id: "claim_ledger_bdo",
    work_item_id: "content_work_item_bdo",
    reviewed_by: "wilku",
    entries: [
      {
        id: "claim_general_bdo",
        claim_text: "Ekologus pomaga firmom uporządkować obowiązki BDO.",
        claim_type: "service_claim" as const,
        status: "allowed_with_evidence" as const,
        strength: "strong" as const,
        required: false,
        evidence_ids: ["ev_wp_bdo"],
        source_connectors: ["wordpress_ekologus"],
        reason: "Claim ma przypisany dowód źródłowy.",
        reviewer_id: "wilku"
      }
    ]
  };
}

function qualityReview() {
  return {
    review_id: "content_quality_review_bdo",
    work_item_id: "content_work_item_bdo",
    draft_package_id: "draft_package_content_work_item_bdo",
    verdict: "needs_changes" as const,
    evidence_coverage: qualityDimension("pass"),
    claim_safety: qualityDimension("pass"),
    duplicate_risk: qualityDimension("pass"),
    usefulness: qualityDimension("needs_changes"),
    service_fit: qualityDimension("pass"),
    search_intent_fit: qualityDimension("pass"),
    buyer_problem_fit: qualityDimension("pass"),
    cta_quality: qualityDimension("needs_changes"),
    factual_precision: qualityDimension("pass"),
    polish_language_quality: qualityDimension("pass"),
    internal_link_fit: qualityDimension("pass"),
    measurement_readiness: qualityDimension("pass"),
    blockers: [],
    findings: [],
    revision_instructions: [
      {
        id: "content_revision_bdo_cta",
        affected_section: "CTA",
        change: "Doprecyzuj CTA bez obietnicy wyniku.",
        reason: "CTA musi prowadzić do bezpiecznej decyzji.",
        required_evidence_ids: ["ev_gsc_bdo"],
        forbidden_claims_to_avoid: ["gwarancja efektu"],
        human_review_checklist_additions: ["Sprawdź CTA"]
      }
    ],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    safe_next_step: "Popraw CTA i ponów review."
  };
}

function qualityDimension(status: "pass" | "needs_changes" | "blocked") {
  return {
    status,
    label: status === "pass" ? "OK" : "Wymaga poprawki",
    reason: "Kontrola jakości ma jasny wynik."
  };
}

function revisionPlan() {
  return {
    id: "content_revision_plan_bdo",
    work_item_id: "content_work_item_bdo",
    quality_review_id: "content_quality_review_bdo",
    status: "ready",
    draft_revision_allowed: true,
    instructions: qualityReview().revision_instructions,
    blockers: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    safe_next_step: "Zastosuj tylko wskazane poprawki."
  };
}

function inventoryResolution() {
  return {
    status: "resolved",
    recommended_mode: "preserve",
    records: [
      {
        id: "inventory_bdo",
        url: "https://ekologus.pl/bdo/",
        final_canonical_url: "https://ekologus.pl/bdo/",
        intended_final_url: "https://ekologus.pl/bdo/",
        preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
        content_status: "published",
        source_connectors: ["wordpress_ekologus"],
        evidence_ids: ["ev_wp_bdo"],
        title: "BDO dla firm",
        h1: "BDO dla firm",
        topic_tags: ["bdo"]
      }
    ],
    similar_existing_urls: ["https://ekologus.pl/bdo/"],
    blockers: [],
    evidence_ids: ["ev_wp_bdo"],
    source_connectors: ["wordpress_ekologus"],
    next_step: "Zacznij od preserve-first."
  };
}

function preflightVerdict(status: string) {
  return {
    status,
    recommended_mode: "preserve",
    create_allowed: false,
    sales_brief_allowed: status !== "plan_allowed",
    draft_allowed: status === "draft_allowed",
    wordpress_draft_allowed: false,
    final_canonical_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    similar_existing_urls: ["https://ekologus.pl/bdo/"],
    blockers: [],
    blocked_claims: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    next_step: "Przejdź do kolejnego kroku."
  };
}

function salesBrief() {
  return {
    id: "sales_brief_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    topic: "BDO dla firm",
    operations_context: {
      enrichment_id: "content_opportunity_enrichment_content_work_item_bdo",
      intent_label: "intencja ryzyka lub obowiązku",
      recommended_mode: "refresh" as const,
      safe_next_step: "Przygotuj preserve-first brief.",
      source_fact_ids: ["source_fact_queries_bdo"]
    },
    target_reader: "właściciel firmy",
    buyer_problem: "nie wie, jak podejść do BDO",
    buyer_trigger: "zbliża się kontrola",
    search_intent: "informacyjno-usługowy",
    service_fit: "obsługa środowiskowa",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    existing_content_plan: "Zacznij od istniejącej treści.",
    h1_direction: "BDO dla firm",
    h2_direction: ["Kogo dotyczy BDO"],
    faq_direction: ["Czy każda firma musi mieć BDO?"],
    cta_direction: "Skontaktuj się z Ekologus.",
    internal_link_direction: ["https://ekologus.pl/kontakt/"],
    source_facts: [
      {
        evidence_id: "ev_gsc_bdo",
        source_connector: "google_search_console",
        summary: "GSC pokazuje popyt na temat BDO."
      }
    ],
    knowledge_card_ids: [
      "ekologus_service_environmental_compliance",
      "ekologus_cta_consultation_without_guarantee",
      "ekologus_evidence_live_connector_requirement"
    ],
    knowledge_constraints: [
      {
        card_id: "ekologus_evidence_live_connector_requirement",
        constraint_type: "evidence_requirement" as const,
        label: "Live evidence i source connector są wymagane",
        reason: "Brak evidence ID oznacza brak rekomendacji."
      }
    ],
    signal_quality: {
      status: "review_required" as const,
      status_label: "sygnał użyteczny, ale wymaga review",
      reason: "Brief ma ślad dowodowy, ale wiedza nadal wymaga decyzji człowieka.",
      evidence_id_count: 2,
      source_connector_count: 2,
      source_fact_count: 1,
      missing_evidence_count: 0,
      knowledge_constraint_count: 1,
      review_required_knowledge_card_count: 1,
      measurement_baseline_ready: true,
      safe_next_step: "Pokaż brief Wilkowi z ograniczeniami wiedzy."
    },
    forbidden_claims: [],
    missing_evidence: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    measurement_plan: {
      measurement_window_id: "measurement_window_content_work_item_bdo",
      metrics_to_watch: ["GSC clicks"],
      baseline_source_connectors: ["google_search_console"],
      baseline_evidence_ids: ["ev_gsc_bdo"],
      measurement_readiness_label: "baza pomiaru do zaplanowania",
      measurement_readiness_reason: "WILQ ma bazę planu pomiaru.",
      earliest_verdict_note: "Nie oceniaj przed końcem okna.",
      success_claim_rule: "Nie claimuj sukcesu bez danych."
    },
    human_review_required: true,
    draft_allowed: false
  };
}

function salesBriefSeed() {
  return {
    target_reader: "właściciel firmy",
    buyer_problem: "nie wie, jak podejść do BDO",
    buyer_trigger: "zbliża się kontrola",
    search_intent: "informacyjno-usługowy",
    service_fit: "obsługa środowiskowa",
    h1_direction: "BDO dla firm",
    h2_direction: ["Kogo dotyczy BDO"],
    faq_direction: ["Czy każda firma musi mieć BDO?"],
    cta_direction: "Skontaktuj się z Ekologus.",
    internal_link_direction: ["https://ekologus.pl/kontakt/"],
    source_facts: [
      {
        evidence_id: "ev_gsc_bdo",
        source_connector: "google_search_console",
        summary: "GSC pokazuje popyt na temat BDO."
      }
    ],
    missing_evidence: []
  };
}

function draftPackage() {
  return {
    id: "draft_package_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_id: "claim_ledger_bdo",
    draft_kind: "outline" as const,
    title: "BDO dla firm",
    sections: [],
    section_to_evidence_map: [],
    claims_used: [],
    claims_removed_or_blocked: [],
    human_review_questions: ["Czy to brzmi jak Ekologus?"],
    publish_ready: false
  };
}

function structuredDraftOutput() {
  return {
    draft_kind: "section_draft" as const,
    language: "pl-PL" as const,
    title: "BDO dla firm",
    meta_title: "BDO dla firm",
    meta_description: "Sprawdź, kiedy warto skonsultować BDO.",
    h1: "BDO dla firm",
    sections: [
      {
        heading: "Kogo dotyczy BDO",
        body_markdown: "BDO warto sprawdzić na podstawie sytuacji firmy.",
        evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
        claims_used: ["Ekologus pomaga firmom uporządkować obowiązki BDO."]
      }
    ],
    faq: ["Czy każda firma musi mieć BDO?"],
    cta: "Skontaktuj się z Ekologus, żeby omówić sytuację firmy.",
    internal_links: ["https://ekologus.pl/kontakt/"],
    source_facts_used: ["ev_gsc_bdo", "ev_wp_bdo"],
    claims_needing_review: [],
    forbidden_claims_avoided: ["Ta treść zwiększy liczbę leadów."],
    human_review_checklist: ["Czy to brzmi jak Ekologus?"],
    publish_ready: false as const
  };
}

function humanReview() {
  return {
    id: "human_review_bdo",
    work_item_id: "content_work_item_bdo",
    stage: "draft_package",
    reviewed_by: "wilku",
    decision: "approved",
    notes: "Może iść dalej.",
    checked_items: ["claimy sprawdzone"],
    evidence_ids: ["ev_gsc_bdo"],
    blocked_claims_handled: [],
    draft_package_id: "draft_package_content_work_item_bdo"
  };
}

function wordpressHandoff() {
  return {
    id: "wordpress_draft_handoff_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    draft_package_id: "draft_package_content_work_item_bdo",
    human_review_id: "human_review_bdo",
    audit_id: "audit_bdo",
      connector: "wordpress_ekologus" as const,
      operation_type: "create_wordpress_draft" as const,
      status: "prepared" as const,
      post_status: "draft" as const,
    title: "BDO dla firm",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    publish_allowed: false,
    destructive_update_allowed: false
  };
}

function wordpressDraftExecutionResult() {
  return {
    status: "dry_run_ready",
    mode: "dry_run",
    boundary: {
      allowed_operation: "create_wordpress_draft",
      dry_run_default: true,
      live_write_enabled: false,
      live_adapter_configured: false,
      publish_allowed: false,
      destructive_update_allowed: false
    },
    payload: {
      connector: "wordpress_ekologus",
      endpoint_kind: "posts",
      post_status: "draft",
      title: "BDO dla firm",
      content_markdown: "Szkic treści do review.",
      final_canonical_url: "https://ekologus.pl/bdo/",
      evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
      publish_allowed: false,
      destructive_update_allowed: false
    },
    wordpress_post_id: null,
    external_write_attempted: false,
    blockers: []
  };
}

function measurementWindow() {
  return {
    id: "measurement_window_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    content_url: "https://ekologus.pl/bdo/",
    baseline_period: { start: "2026-05-01", end: "2026-05-31" },
    observation_period: { start: "2026-07-01", end: "2026-07-31" },
    earliest_verdict_date: "2026-08-01",
    allowed_metrics: ["gsc_clicks"],
    source_connectors: ["google_search_console"],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    status: "planned",
    handoff_id: "wordpress_draft_handoff_content_work_item_bdo",
    success_claim_allowed: false
  };
}
