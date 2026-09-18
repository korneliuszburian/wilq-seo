import { describe, expect, it } from "vitest";

import { ContentInventoryCatalogResponseSchema } from "./index";

const blockedReadiness = {
  status: "blocked",
  status_label: "Zablokowane",
  authoring_inventory_receipt: {
    status: "missing",
    receipt_id: null,
    receipt_digest: null,
    evidence_id: null,
    collected_at: null,
    freshness: "missing"
  },
  evidence_acquisition: {
    recorded_status: "missing",
    current_status: "missing",
    run_id: null,
    run_digest: null,
    evidence_ids: [],
    subject_kind: null,
    subject_id: null,
    freshness: "missing",
    blockers: [],
    safe_next_step: "Uruchom exact evidence acquisition."
  },
  research_proposal: {
    status: "missing",
    proposal_id: null,
    proposal_digest: null,
    acquisition_run_id: null,
    review_required: false,
    approved: false,
    blockers: [],
    safe_next_step: "Najpierw uzyskaj acquisition."
  },
  identity: {
    status: "missing",
    binding_id: null,
    binding_digest: null,
    blockers: [],
    safe_next_step: "Zwiąż exact identity."
  },
  service_card: {
    status: "missing",
    card_id: null,
    card_status: null,
    evidence_ids: [],
    source_connectors: [],
    blockers: [{ code: "service_card_missing", reason: "Brak exact card.", evidence_ids: [], safe_next_step: "Zweryfikuj card." }],
    safe_next_step: "Zweryfikuj card."
  },
  promotion: {
    status: "blocked",
    receipt_id: null,
    source_fact_id: null,
    blockers: [{ code: "promotion_identity_required", reason: "Brak identity.", evidence_ids: [], safe_next_step: "Zwiąż identity." }],
    safe_next_step: "Zwiąż identity."
  },
  blockers: [{ code: "current_catalog_observation_missing", reason: "Brak obserwacji.", evidence_ids: [], safe_next_step: "Odśwież inventory." }],
  generation_allowed: false,
  safe_next_step: "Odśwież inventory."
} as const;

const journalReadiness = {
  status: "blocked",
  journal_record_count: 214,
  catalog_coverage_status: "unknown",
  content_evidence_readiness: {
    total_count: 214,
    blocked_count: 214,
    review_required_count: 0,
    ready_for_researcher_count: 0,
    missing_count: 0,
    authoring_receipt_current_count: 0,
    authoring_receipt_stale_count: 0,
    authoring_receipt_missing_count: 214,
    acquisition_ready_count: 0,
    acquisition_blocked_count: 0,
    acquisition_missing_count: 214,
    research_ready_count: 0,
    research_blocked_count: 0,
    research_missing_count: 214,
    identity_exact_current_count: 0,
    identity_blocked_count: 0,
    identity_missing_count: 214,
    service_card_approved_current_count: 0,
    service_card_review_required_count: 0,
    promotion_approved_current_count: 0,
    generation_allowed: false
  },
  rows: Array.from({ length: 214 }, (_, index) => ({
    canonical_path: `/historyczna-pozycja-${index + 1}`,
    historical_as_of: "2026-08-28",
    content_kind: "editorial",
    final_disposition: index % 2 === 0 ? "keep" : "redirect",
    historical_next_action: "review",
    operational_owner: index % 2 === 0 ? "WILQ content workflow" : "WILQ sitemap operations",
    production_cohort: index % 2 === 0,
    current_catalog_state: "not_observed",
    current_catalog_observation: null,
    content_evidence_readiness: blockedReadiness
  })),
  caveat: "Brak pełnego bieżącego coverage; historyczne decyzje nie są runtime authority.",
  safe_next_step: "Uzupełnij bieżący inventory albo zachowaj brak obserwacji jako blocker."
};

describe("ContentInventoryCatalogResponseSchema journal readiness", () => {
  it("preserves the blocked 214-row historical-scope projection at the API boundary", () => {
    const parsed = ContentInventoryCatalogResponseSchema.parse({
      status: "blocked",
      total_count: 139,
      ready_count: 0,
      partial_count: 0,
      blocked_count: 139,
      items: [],
      source_connectors: ["wordpress_ekologus"],
      evidence_ids: ["ev_wp_current"],
      coverage: {
        status: "unknown",
        returned_count: 139,
        caveat: "Coverage jest niepełne."
      },
      journal_readiness: journalReadiness
    });

    expect(parsed.journal_readiness).toMatchObject({
      status: "blocked",
      journal_record_count: 214,
      catalog_coverage_status: "unknown",
      content_evidence_readiness: {
        total_count: 214,
        generation_allowed: false
      }
    });
    expect(parsed.journal_readiness?.rows).toHaveLength(214);
    expect(parsed.journal_readiness?.rows[0]).toMatchObject({
      final_disposition: "keep",
      current_catalog_state: "not_observed",
      content_evidence_readiness: {
        status: "blocked",
        generation_allowed: false
      }
    });
  });

  it("rejects a readiness row that claims generation authority", () => {
    expect(() => ContentInventoryCatalogResponseSchema.parse({
      status: "blocked",
      total_count: 0,
      items: [],
      coverage: { status: "unknown", returned_count: 0, caveat: "Brak coverage." },
      journal_readiness: {
        ...journalReadiness,
        rows: [{ ...journalReadiness.rows[0], content_evidence_readiness: { ...blockedReadiness, generation_allowed: true } }]
      }
    })).toThrow();
  });
});
