import { afterEach, describe, expect, it, vi } from "vitest";
import {
  actionApiPath,
  applyAction,
  createContentNewPageFoundation,
  createContentNewPageInitialDraft,
  reviewContentNewPageRevision,
  getActionMutationReadiness,
  getActionsMutationReadiness,
  getContentWorkItemSemanticReview,
  getContentRegulatorySourceSnapshot,
  postContentRegulatorySourceReview,
  postContentWorkItemInitialDraft,
  previewAction
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
  it("binds a source review to the exact captured official snapshot", async () => {
    const snapshot = {
      status: "captured",
      snapshot: {
        snapshot_id: "regulatory_snapshot_scope",
        candidate_id: "bdo_registration_scope_2026_07_31",
        profile_id: "bdo",
        profile_version: "2026-07",
        source_url: "https://bdo.mos.gov.pl/baza-wiedzy/kto-podlega-pod-obowiazek-rejestracji/",
        content_digest: "a".repeat(64),
        content_type: "text/html",
        byte_length: 128,
        observed_at: "2026-07-31T12:00:00Z"
      },
      reason: "Pobrano snapshot.",
      safe_next_step: "Sprawdź źródło."
    };
    const request = {
      candidate_id: snapshot.snapshot.candidate_id,
      expected_source_url: snapshot.snapshot.source_url,
      expected_profile_version: snapshot.snapshot.profile_version,
      expected_source_snapshot_id: snapshot.snapshot.snapshot_id,
      expected_source_snapshot_digest: snapshot.snapshot.content_digest,
      reviewed_fact: "Zakres obowiązku wymaga oceny względem konkretnej działalności.",
      covered_requirement_ids: ["bdo_scope"],
      decision: "accepted" as const,
      reviewer: "Wilku"
    };
    const review = {
      review_id: "regulatory_review_scope",
      ...snapshot.snapshot,
      source_snapshot_id: snapshot.snapshot.snapshot_id,
      source_snapshot_digest: snapshot.snapshot.content_digest,
      source_title: "BDO: zakres obowiązku",
      observed_on: "2026-07-31",
      service_card_ids: ["ekologus_service_bdo_reporting"],
      reviewed_fact: request.reviewed_fact,
      covered_requirement_ids: request.covered_requirement_ids,
      decision: request.decision,
      reviewer: request.reviewer,
      reviewed_at: "2026-07-31T12:01:00Z"
    };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(url)).pathname;
      if (path.endsWith("/snapshot")) {
        return new Response(JSON.stringify(snapshot), { status: 200 });
      }
      expect(path).toBe("/api/content/regulatory-source-reviews");
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual(request);
      return new Response(JSON.stringify(review), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const captured = await getContentRegulatorySourceSnapshot(request.candidate_id);
    const result = await postContentRegulatorySourceReview(request);

    expect(captured.status).toBe("captured");
    expect("code" in result).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

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

  it("reads a typed semantic-review blocker for one exact revision", async () => {
    const response = {
      status: "blocked",
      work_item_id: "content_work_item_bdo",
      revision_id: "content_revision_bdo",
      revision_digest: "a".repeat(64),
      review: null,
      run_id: null,
      runtime: {
        status: "blocked",
        run_id: null,
        thread_id: null,
        turn_id: null,
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      blockers: [{
        code: "source_material_review_required",
        label: "Materiał wymaga kontroli",
        reason: "Źródłowy materiał nie został jeszcze zatwierdzony.",
        next_step: "Sprawdź materiał.",
        source_codes: ["wordpress_material_review_required"]
      }],
      safe_next_step: "Sprawdź materiał.",
      publish_ready: false,
      human_review_required: true,
      action_object_created: false
    } as const;
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      expect(new URL(String(url)).pathname).toBe(
        "/api/content/work-items/content_work_item_bdo/draft-revisions/content_revision_bdo/semantic-review"
      );
      return new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await getContentWorkItemSemanticReview(
      "content_work_item_bdo",
      "content_revision_bdo"
    );

    expect(result.blockers[0]?.code).toBe("source_material_review_required");
    expect(result.publish_ready).toBe(false);
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

});
