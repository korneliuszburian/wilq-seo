import { afterEach, describe, expect, it, vi } from "vitest";
import {
  actionApiPath,
  applyAction,
  createContentNewPageFoundation,
  createContentNewPageInitialDraft,
  reviewContentNewPageRevision,
  getActionMutationReadiness,
  getActionsMutationReadiness,
  getContentWorkItemQueue,
  getContentWorkItemSemanticReview,
  postContentWorkItemCodexSectionProposal,
  postContentWorkItemInitialDraft,
  postContentWorkItemSemanticReview,
  previewAction,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview
} from "./api";

const responseByPath: Record<string, unknown> = {
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
  it("posts an exact new-page foundation and preserves its typed lineage", async () => {
    const foundation = {
      foundation_id: "content_new_page_foundation_a",
      work_item_id: "content_work_item_new_page_a",
      brief_id: "content_new_page_brief_a",
      brief_digest: "a".repeat(64),
      overlap_digest: "b".repeat(64),
      overlap_evidence_ids: ["ev_inventory_a"],
      service_card_id: "knowledge_service_a",
      service_card_digest: "c".repeat(64),
      service_label: "Usługa A",
      service_evidence_ids: ["ev_service_a"],
      confirmed_by: "Wilku",
      created_at: "2026-07-27T10:00:00Z"
    };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(new URL(String(url)).pathname).toBe(
        "/api/content/new-page-briefs/content_new_page_brief_a/planning-foundation"
      );
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        expected_brief_digest: foundation.brief_digest,
        expected_overlap_digest: foundation.overlap_digest,
        service_card_id: foundation.service_card_id,
        confirmed_by: foundation.confirmed_by
      });
      return new Response(JSON.stringify({
        status: "created",
        foundation,
        reason: "Podstawa planowania jest związana z dokładnym briefem.",
        safe_next_step: "Przygotuj plan dokumentu w kolejnym etapie workflow."
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createContentNewPageFoundation("content_new_page_brief_a", {
      expected_brief_digest: foundation.brief_digest,
      expected_overlap_digest: foundation.overlap_digest,
      service_card_id: foundation.service_card_id,
      confirmed_by: foundation.confirmed_by
    });

    expect(result.foundation).toMatchObject({
      foundation_id: foundation.foundation_id,
      work_item_id: foundation.work_item_id,
      brief_digest: foundation.brief_digest,
      overlap_digest: foundation.overlap_digest,
      service_card_digest: foundation.service_card_digest
    });
  });

  it("posts an exact new-page initial-draft request without a public URL", async () => {
    const request = {
      expected_proposal_id: "content_planning_proposal_a",
      expected_planning_digest: "a".repeat(64),
      expected_planning_input_digest: "b".repeat(64),
      requested_by: "Wilku"
    };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(new URL(String(url)).pathname).toBe(
        "/api/content/new-page-briefs/content_new_page_brief_a/initial-draft"
      );
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual(request);
      return new Response(JSON.stringify({
        status: "blocked",
        work_item_id: "content_work_item_new_page_a",
        proposal_id: request.expected_proposal_id,
        run_id: null,
        revision: null,
        runtime: {
          status: "not_started",
          thread_id: null,
          turn_id: null,
          external_call_attempted: false
        },
        blockers: [{
          code: "planning_not_ready",
          label: "Nie utworzono dokumentu nowej strony",
          reason: "Plan nie jest gotowy do utworzenia dokumentu.",
          next_step: "Wygeneruj aktualny plan."
        }],
        safe_next_step: "Zatwierdź plan.",
        publish_ready: false
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createContentNewPageInitialDraft("content_new_page_brief_a", request);

    expect(result.status).toBe("blocked");
    expect(result.blockers[0]?.code).toBe("planning_not_ready");
  });

  it("posts exact new-page revision review with its current digest", async () => {
    const request = {
      expected_revision_digest: "c".repeat(64),
      reviewed_by: "Wilku",
      decision: "approved" as const,
      notes: "",
      checked_items: ["Sprawdzono dokument."],
      evidence_ids: ["ev_service"]
    };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(new URL(String(url)).pathname).toBe(
        "/api/content/new-page-briefs/content_new_page_brief_a/draft-revisions/content_revision_new_page_a/review"
      );
      expect(JSON.parse(String(init?.body))).toEqual(request);
      return new Response(JSON.stringify({
        status: "recorded",
        review: {
          decision_id: "content_revision_decision_new_page_a",
          decision_number: 1,
          work_item_id: "content_work_item_new_page_a",
          revision_id: "content_revision_new_page_a",
          revision_digest: request.expected_revision_digest,
          reviewed_by: request.reviewed_by,
          decision: request.decision,
          notes: request.notes,
          checked_items: request.checked_items,
          evidence_ids: request.evidence_ids,
          created_at: "2026-07-28T18:00:00Z"
        }
      }), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await reviewContentNewPageRevision(
      "content_new_page_brief_a",
      "content_revision_new_page_a",
      request
    );

    expect(result.status).toBe("recorded");
    if (result.status !== "recorded") {
      throw new Error("Expected recorded new-page revision review response.");
    }
    expect(result.review.revision_digest).toBe(request.expected_revision_digest);
  });

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
        claim_ids: [],
        source_material_ids: [],
        knowledge_card_ids: []
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
      selected_cta_ids: [],
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
      selected_section_ids: [],
      selected_cta_ids: [],
      requested_by: "wilku"
    });
  });

  it("posts an exact initial-draft binding and preserves a typed conflict", async () => {
    const blocked = {
      status: "conflict",
      work_item_id: "content/work item",
      proposal_id: "proposal/1",
      run_id: null,
      revision: null,
      runtime: {
        status: "not_started",
        thread_id: null,
        turn_id: null,
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      blockers: [{
        code: "revision_already_exists",
        label: "Pierwsza wersja już istnieje",
        reason: "Initial draft może utworzyć tylko pierwszą rewizję.",
        next_step: "Otwórz zapisaną wersję.",
        source_codes: []
      }],
      safe_next_step: "Otwórz zapisaną wersję.",
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

    const result = await postContentWorkItemInitialDraft({
      expected_proposal_id: "proposal/1",
      expected_planning_digest: "a".repeat(64),
      expected_planning_input_digest: "b".repeat(64),
      requested_by: "wilku"
    }, "content/work item");

    expect(result).toEqual(blocked);
    expect(new URL(String(fetchMock.mock.calls[0]?.[0])).pathname).toBe(
      "/api/content/work-items/content%2Fwork%20item/initial-draft"
    );
    expect(JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))).toEqual({
      expected_proposal_id: "proposal/1",
      expected_planning_digest: "a".repeat(64),
      expected_planning_input_digest: "b".repeat(64),
      requested_by: "wilku"
    });
  });

  it("reads and posts an exact revision-bound semantic review", async () => {
    const dimensions = [
      "answer_directness",
      "completeness",
      "logical_flow",
      "specificity",
      "repetition",
      "search_intent_fit",
      "buyer_fit",
      "credibility",
      "conversion_clarity"
    ] as const;
    const review = {
      review_id: "semantic-review-1",
      work_item_id: "content/work item",
      revision_id: "revision/1",
      revision_digest: "c".repeat(64),
      criteria_version: "wilq_semantic_content_review_v1",
      codex_run_id: "codex-run-1",
      status: "needs_changes",
      dimensions: dimensions.map((dimension) => ({
        dimension,
        status: dimension === "answer_directness" ? "needs_changes" : "strong",
        reason: "Ocena dokładnej wersji.",
        affected_targets: ["section-1"]
      })),
      findings: [{
        finding_id: "semantic-finding-1",
        dimension: "answer_directness",
        severity: "medium",
        label: "Za wolne wejście w odpowiedź",
        reason: "Czytelnik za późno dostaje decyzję.",
        instruction: "Przenieś odpowiedź na początek.",
        affected_targets: ["section-1"],
        evidence_ids: ["ev-gsc"]
      }],
      evidence_ids: ["ev-gsc"],
      source_connectors: ["google_search_console"],
      requested_by: "wilku",
      created_at: "2026-07-16T18:00:00Z",
      safe_next_step: "Wybierz sekcję do poprawy.",
      publish_ready: false,
      human_review_required: true,
      action_object_created: false
    } as const;
    const response = {
      status: "ready",
      work_item_id: "content/work item",
      revision_id: "revision/1",
      revision_digest: "c".repeat(64),
      review,
      run_id: "codex-run-1",
      runtime: {
        status: "not_started",
        thread_id: null,
        turn_id: null,
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      blockers: [],
      safe_next_step: "Wybierz sekcję do poprawy.",
      publish_ready: false,
      human_review_required: true,
      action_object_created: false
    } as const;
    const fetchMock = vi.fn(async (_url: RequestInfo | URL, _init?: RequestInit) => {
      void _url;
      void _init;
      return new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await getContentWorkItemSemanticReview("content/work item", "revision/1");
    await postContentWorkItemSemanticReview({
      expected_revision_digest: "c".repeat(64),
      requested_by: "wilku"
    }, "content/work item", "revision/1");

    expect(new URL(String(fetchMock.mock.calls[0]?.[0])).pathname).toBe(
      "/api/content/work-items/content%2Fwork%20item/draft-revisions/revision%2F1/semantic-review"
    );
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body))).toEqual({
      expected_revision_digest: "c".repeat(64),
      requested_by: "wilku"
    });
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

});

function draftRevision() {
  return {
    schema_version: "wilq_content_draft_revision_v1",
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
    faq: [],
    cta_blocks: [],
    internal_links: [],
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
