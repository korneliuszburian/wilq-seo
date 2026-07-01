import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemQueue,
  getContentWorkItemSnapshot,
  postContentWorkItemDraftPackage,
  postContentWorkItemHumanReview,
  postContentWorkItemMeasurementWindow,
  postContentWorkItemPreflight,
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemSalesBrief,
  postContentWorkItemStructuredDraftGeneration,
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressDraftExecution,
  postContentWorkItemWordPressDraftHandoff,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemStructuredDraftRuntimeRequest
} from "./api";

const responseByPath: Record<string, unknown> = {
  "/api/content/work-items/queue": contentQueueResponse(),
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
  "/api/content/work-items/structured-draft-generation": {
    item: workItem(),
    structured_generation_result: {
      contract: structuredDraftGenerationContract(),
      blockers: []
    }
  },
  "/api/content/work-items/structured-draft-runtime": {
    runtime_result: structuredDraftRuntimeResult()
  },
  "/api/content/work-items/structured-draft-preview": {
    preview_result: {
      preview: structuredDraftPreview(),
      blockers: []
    }
  },
  "/api/content/work-items/content_work_item_bdo/structured-draft-preview": {
    preview_result: {
      preview: structuredDraftPreview(),
      blockers: []
    }
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
  }
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("content workflow API helpers", () => {
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

    expect(snapshot.preflight.item.id).toBe("content_work_item_bdo");
    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/content/work-items/snapshot"
    ]);
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
    await getContentWorkItemSnapshot("content_work_item_bdo");
    await postContentWorkItemPreflight({ item: workItem() });
    await postContentWorkItemSalesBrief({ item: workItem(), claim_ledger: {}, seed: {} });
    await postContentWorkItemDraftPackage({ item: workItem(), claim_ledger: {}, seed: {} });
    await postContentWorkItemStructuredDraftGeneration({
      item: workItem(),
      sales_brief: salesBrief(),
      claim_ledger: {},
      draft_package: draftPackage()
    });
    await postContentWorkItemStructuredDraftRuntime({
      contract: structuredDraftGenerationContract(),
      model: "gpt-5",
      mode: "dry_run"
    });
    await postContentWorkItemStructuredDraftPreview({
      contract: structuredDraftGenerationContract(),
      output: structuredDraftOutput()
    });
    await postContentWorkItemStructuredDraftPreview(
      {
        contract: structuredDraftGenerationContract(),
        output: structuredDraftOutput()
      },
      "content_work_item_bdo"
    );
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
      "/api/content/work-items/content_work_item_bdo/snapshot",
      "/api/content/work-items/preflight",
      "/api/content/work-items/sales-brief",
      "/api/content/work-items/draft-package",
      "/api/content/work-items/structured-draft-generation",
      "/api/content/work-items/structured-draft-runtime",
      "/api/content/work-items/structured-draft-preview",
      "/api/content/work-items/content_work_item_bdo/structured-draft-preview",
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
});

function workflowSnapshot() {
  return {
    preflight: responseByPath["/api/content/work-items/preflight"],
    sales_brief: responseByPath["/api/content/work-items/sales-brief"],
    draft_package: responseByPath["/api/content/work-items/draft-package"],
    structured_generation: responseByPath["/api/content/work-items/structured-draft-generation"],
    human_review: responseByPath["/api/content/work-items/human-review"],
    wordpress_handoff: responseByPath["/api/content/work-items/wordpress-draft-handoff"],
    measurement_window: responseByPath["/api/content/work-items/measurement-window"]
  };
}

function contentQueueResponse() {
  return {
    queue_status: "ready",
    candidate_count: 1,
    actionable_candidate_count: 1,
    minimum_actionable_candidate_count: 1,
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
          status: "ready",
          label: "pomiar gotowy",
          reason: "GSC i GA4 są dostępne.",
          source_connectors: ["google_search_console", "google_analytics_4"]
        },
        safe_next_step: "Otwórz workflow i przygotuj szkic do review.",
        blockers: []
      }
    ],
    blockers: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"]
  };
}

function workItem(overrides: Record<string, unknown> = {}) {
  return {
    id: "content_work_item_bdo",
    topic: "BDO dla firm",
    source_public_url: "https://ekologus.pl/bdo/",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
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
    claim_ledger: {},
    structured_output: structuredDraftOutput(),
    duplicate_risk: "clear"
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
    forbidden_claims: [],
    missing_evidence: [],
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    source_connectors: ["google_search_console", "wordpress_ekologus"],
    measurement_plan: {
      measurement_window_id: "measurement_window_content_work_item_bdo",
      metrics_to_watch: ["GSC clicks"],
      earliest_verdict_note: "Nie oceniaj przed końcem okna.",
      success_claim_rule: "Nie claimuj sukcesu bez danych."
    },
    human_review_required: true,
    draft_allowed: false
  };
}

function draftPackage() {
  return {
    id: "draft_package_content_work_item_bdo",
    work_item_id: "content_work_item_bdo",
    brief_id: "sales_brief_content_work_item_bdo",
    claim_ledger_id: "claim_ledger_bdo",
    draft_kind: "outline",
    title: "BDO dla firm",
    sections: [],
    section_to_evidence_map: [],
    claims_used: [],
    claims_removed_or_blocked: [],
    human_review_questions: ["Czy to brzmi jak Ekologus?"],
    publish_ready: false
  };
}

function structuredDraftGenerationContract(): NonNullable<
  ContentWorkItemStructuredDraftRuntimeRequest["contract"]
> {
  return {
    schema_name: "wilq_content_structured_draft_v1",
    strict_schema: true,
    model_input: {
      work_item_id: "content_work_item_bdo",
      language: "pl-PL",
      draft_kind: "section_draft",
      title: "BDO dla firm",
      final_canonical_url: "https://ekologus.pl/bdo/",
      source_public_url: "https://ekologus.pl/bdo/",
      preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
      target_reader: "właściciel firmy",
      buyer_problem: "nie wie, jak podejść do BDO",
      buyer_trigger: "zbliża się kontrola",
      search_intent: "informacyjno-usługowy",
      service_fit: "obsługa środowiskowa",
      cta_direction: "Skontaktuj się z Ekologus.",
      sections: [
        {
          heading: "Kogo dotyczy BDO",
          purpose: "Sekcja konspektu do napisania po sprawdzeniu planu.",
          evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
          draft_notes: ["Zachowaj kierunek H1"]
        }
      ],
      source_facts: [
        {
          evidence_id: "ev_gsc_bdo",
          source_connector: "google_search_console",
          summary: "GSC pokazuje popyt na temat BDO."
        }
      ],
      claims_allowed: ["Ekologus pomaga firmom uporządkować obowiązki BDO."],
      claims_removed_or_blocked: [],
      human_review_questions: ["Czy to brzmi jak Ekologus?"]
    },
    output_schema: {
      type: "object",
      additionalProperties: false,
      properties: { sections: { type: "array" } }
    },
    system_instruction: "Pisz wyłącznie z przekazanych faktów.",
    user_instruction: "Przygotuj ustrukturyzowany szkic treści dla WILQ.",
    publish_ready: false
  };
}

function structuredDraftRuntimeResult() {
  return {
    status: "dry_run_ready",
    request_payload: {
      model: "gpt-5",
      input: [
        {
          role: "system",
          content: "Pisz wyłącznie z przekazanych faktów."
        },
        {
          role: "user",
          content: "Przygotuj ustrukturyzowany szkic treści dla WILQ."
        }
      ],
      text: {
        format: {
          type: "json_schema",
          name: "wilq_content_structured_draft_v1",
          strict: true,
          schema: {
            type: "object",
            additionalProperties: false,
            properties: { sections: { type: "array" } }
          }
        }
      },
      temperature: 0.2,
      max_output_tokens: 4000
    },
    output: null,
    external_call_attempted: false,
    blockers: []
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

function structuredDraftPreview() {
  const output = structuredDraftOutput();
  return {
    title: output.title,
    meta_title: output.meta_title,
    meta_description: output.meta_description,
    h1: output.h1,
    sections: output.sections,
    faq: output.faq,
    cta: output.cta,
    internal_links: output.internal_links,
    source_facts_used: output.source_facts_used,
    forbidden_claims_avoided: output.forbidden_claims_avoided,
    human_review_checklist: output.human_review_checklist,
    publish_ready: false
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
