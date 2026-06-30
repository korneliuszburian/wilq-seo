import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemSnapshot,
  postContentWorkItemDraftPackage,
  postContentWorkItemHumanReview,
  postContentWorkItemMeasurementWindow,
  postContentWorkItemPreflight,
  postContentWorkItemSalesBrief,
  postContentWorkItemStructuredDraftGeneration,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressDraftHandoff,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemStructuredDraftRuntimeRequest
} from "./api";

const responseByPath: Record<string, unknown> = {
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
  "/api/content/work-items/snapshot/audit": {
    item: workItem(),
    handoff_result: { handoff: wordpressHandoff(), blockers: [] }
  },
  "/api/content/work-items/wordpress-draft-handoff": {
    item: workItem(),
    handoff_result: { handoff: wordpressHandoff(), blockers: [] }
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

  it("posts every Goal 002 work item contract to the API-owned endpoint", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      const path = new URL(String(url)).pathname;
      return {
        ok: true,
        json: async () => responseByPath[path]
      } as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

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
    await postContentWorkItemHumanReview({ item: workItem(), review: humanReview() });
    await saveContentWorkItemSnapshotHumanReview({ review: humanReview() });
    await saveContentWorkItemSnapshotAudit({
      audit: {
        audit_id: "audit_bdo",
        actor: "wilku",
        reason: "Zatwierdzony szkic może trafić do WordPress jako draft.",
        evidence_ids: ["ev_gsc_bdo"],
        human_review_id: "human_review_bdo"
      }
    });
    await postContentWorkItemWordPressDraftHandoff({ item: workItem() });
    await postContentWorkItemMeasurementWindow({
      item: workItem(),
      baseline_period: { start: "2026-05-01", end: "2026-05-31" },
      observation_period: { start: "2026-07-01", end: "2026-07-31" },
      allowed_metrics: ["gsc_clicks"],
      source_connectors: ["google_search_console"]
    });

    expect(fetchMock.mock.calls.map(([url]) => new URL(String(url)).pathname)).toEqual([
      "/api/content/work-items/preflight",
      "/api/content/work-items/sales-brief",
      "/api/content/work-items/draft-package",
      "/api/content/work-items/structured-draft-generation",
      "/api/content/work-items/structured-draft-runtime",
      "/api/content/work-items/human-review",
      "/api/content/work-items/snapshot/human-review",
      "/api/content/work-items/snapshot/audit",
      "/api/content/work-items/wordpress-draft-handoff",
      "/api/content/work-items/measurement-window"
    ]);
  });
});

function workflowSnapshot() {
  return {
    preflight: responseByPath["/api/content/work-items/preflight"],
    sales_brief: responseByPath["/api/content/work-items/sales-brief"],
    draft_package: responseByPath["/api/content/work-items/draft-package"],
    human_review: responseByPath["/api/content/work-items/human-review"],
    wordpress_handoff: responseByPath["/api/content/work-items/wordpress-draft-handoff"],
    measurement_window: responseByPath["/api/content/work-items/measurement-window"]
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
    connector: "wordpress_ekologus",
    operation_type: "create_wordpress_draft",
    status: "prepared",
    post_status: "draft",
    title: "BDO dla firm",
    final_canonical_url: "https://ekologus.pl/bdo/",
    intended_final_url: "https://ekologus.pl/bdo/",
    preview_url: "https://ekologus.dev.proudsite.pl/bdo/",
    evidence_ids: ["ev_gsc_bdo", "ev_wp_bdo"],
    publish_allowed: false,
    destructive_update_allowed: false
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
