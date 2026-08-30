import { describe, expect, it } from "vitest";

import {
  ContentDraftRevisionSchema,
  ContentPlanningProposalRequestSchema,
  ContentPlanningProposalResponseSchema,
  ContentPlanningProposalSchema,
  ContentRefreshPreparationBindingSchema
} from "./contentWorkflow";
import {
  ContentInitialDraftRequestSchema,
  ContentInitialDraftResponseSchema
} from "./content_initial_draft";

const hex = (character: string): string => character.repeat(64);
const workItemId = "content_work_item_operat_wodnoprawny";
const serviceCardId = "ekologus_service_operat_wodnoprawny";
const publicUrl = "https://www.ekologus.pl/analiza-pozwolen-zintegrowanych/";
const binding = {
  authorization_id: `content_refresh_preparation_authorization_${"a".repeat(24)}`,
  authorization_digest: hex("a"),
  classification_run_id: "content_production_classification_operat",
  classification_run_digest: hex("b"),
  decision_set_digest: hex("c"),
  source_packet_row_digest: hex("d"),
  current_work_item_id: workItemId,
  canonical_path: "/analiza-pozwolen-zintegrowanych",
  public_url: publicUrl,
  service_card_id: serviceCardId,
  planning_input_digest: hex("e")
};
const sources = [
  "wordpress",
  "service_profile",
  "gsc",
  "ga4",
  "google_ads",
  "ahrefs",
  "keyword_planner",
  "merchant",
  "localo",
  "social"
].map((source) => ({
  source,
  status: source === "wordpress" ? "used" : "not_applicable",
  reason: "Dokładny fixture kontraktu.",
  landing_match_tiers: [],
  evidence_ids: source === "wordpress" ? ["ev_operat"] : [],
  knowledge_card_ids: source === "service_profile" ? [serviceCardId] : []
}));
const proposal = {
  work_item_id: workItemId,
  planning_digest: hex("f"),
  proposal_id: "content_planning_proposal_operat",
  proposal_version: 1,
  codex_run_id: "codex_planning_operat",
  generation_status: "codex_generated" as const,
  planning_input_digest: binding.planning_input_digest,
  goal: "refresh_existing" as const,
  final_canonical_url: publicUrl,
  service_card_id: serviceCardId,
  service_label: "Analiza pozwoleń zintegrowanych",
  service_selection_confirmed: true,
  human_override_review_required: false,
  target_reader: "Przedsiębiorca",
  buyer_problem: "Brak pewności co do obowiązków.",
  buyer_trigger: "Zmiana inwestycji.",
  search_intent: "Informacyjna.",
  angle: "Najpierw zakres obowiązków.",
  value_proposition: "Bezpieczny następny krok.",
  cta_direction: "Opisz sytuację do weryfikacji.",
  internal_link_directions: [],
  sections: [{
    section_id: "content_planning_proposal_operat_section_01",
    heading: "Co sprawdzić przy pozwoleniu zintegrowanym",
    purpose: "Wyjaśnia pierwszy krok.",
    reader_question: "Od czego zacząć?",
    inventory_disposition: "rewrite" as const,
    inventory_section_id: "inventory_operat_01",
    inventory_heading: "Analiza pozwolenia",
    query_terms: ["analiza pozwolenia zintegrowanego"],
    evidence_ids: ["ev_operat"],
    claim_ids: [],
    source_material_ids: [],
    knowledge_card_ids: [serviceCardId],
    regulatory_requirement_ids: []
  }],
  inventory_mapping: [],
  search_demand: {
    status: "missing" as const,
    gsc_query_rows: [],
    ads_term_rows: [],
    keyword_planner_rows: [],
    source_connectors: [],
    evidence_ids: [],
    optional_ads_status: "not_exactly_mapped" as const,
    safe_next_step: "Sprawdź dokładne dane popytowe."
  },
  page_assets: {
    title: "Analiza pozwoleń zintegrowanych",
    h1: "Analiza pozwolenia zintegrowanego",
    lead: "Najpierw uporządkuj obowiązki.",
    meta_title: "Analiza pozwolenia zintegrowanego — Ekologus",
    meta_description: "Sprawdź obowiązki oraz następny krok."
  },
  faq: [],
  cta_blocks: [],
  internal_links: [],
  conditional_hypotheses: [],
  measurement_plan: {
    metrics_to_watch: [],
    baseline_evidence_ids: [],
    observation_rule: "Sprawdź dane po zamknięciu okna.",
    success_claim_rule: "Nie składaj deklaracji bez zamkniętego pomiaru."
  },
  evidence_ids: ["ev_operat"],
  source_connectors: ["wordpress_ekologus", "service_profile"],
  source_material_ids: [],
  knowledge_card_ids: [serviceCardId],
  refresh_preparation_binding: binding,
  created_at: "2026-08-30T12:00:00Z"
};
const revision = {
  schema_version: "wilq_content_draft_revision_v2" as const,
  revision_id: "content_revision_operat",
  work_item_id: workItemId,
  revision_number: 1,
  base_revision_id: null,
  content_digest: hex("1"),
  draft_package_id: "draft_package_operat",
  draft_package_digest: hex("2"),
  planning_digest: proposal.planning_digest,
  planning_input_digest: binding.planning_input_digest,
  service_card_id: serviceCardId,
  service_digest: hex("3"),
  inventory_digest: hex("4"),
  source_material_ids: [],
  knowledge_card_ids: [serviceCardId],
  source_provenance: [],
  document_kind: "refresh_existing" as const,
  final_canonical_url: publicUrl,
  new_page_document_identity: null,
  title: proposal.page_assets.title,
  page_assets: {
    wordpress_title: proposal.page_assets.title,
    meta_title: proposal.page_assets.meta_title,
    meta_description: proposal.page_assets.meta_description,
    h1: proposal.page_assets.h1,
    lead: proposal.page_assets.lead
  },
  sections: [{
    section_id: proposal.sections[0].section_id,
    heading: proposal.sections[0].heading,
    body_markdown: "Najpierw sprawdź zakres obowiązków i dokumenty.",
    content_html: "<p>Najpierw sprawdź zakres obowiązków i dokumenty.</p>",
    query_terms: proposal.sections[0].query_terms,
    evidence_ids: ["ev_operat"],
    claim_ids: [],
    source_material_ids: [],
    knowledge_card_ids: [serviceCardId]
  }],
  faq: [],
  cta_blocks: [],
  internal_links: [],
  official_source_references: [],
  claim_ledger: null,
  proposal_metadata: {
    source: "codex_app_server" as const,
    codex_run_id: "codex_initial_operat",
    selected_section_headings: [proposal.sections[0].heading],
    section_lineage: [{
      heading: proposal.sections[0].heading,
      evidence_ids: ["ev_operat"],
      claim_ids: [],
      source_material_ids: [],
      knowledge_card_ids: [serviceCardId]
    }],
    selected_cta_ids: [],
    cta_lineage: [],
    quality_verdict: "reviewable" as const,
    quality_finding_codes: [],
    review_scope: "persisted_selected_sections_and_declared_lineage" as const,
    semantic_review_required: true as const,
    refresh_preparation_binding: binding
  },
  refresh_preparation_binding: binding,
  correction_reason: null,
  publish_ready: false as const,
  created_by: "wilku",
  created_at: "2026-08-30T12:05:00Z"
};

describe("classified refresh browser contracts", () => {
  it("round-trips an exact bound plan and revision through public schemas", () => {
    const parsedProposal = ContentPlanningProposalSchema.parse(proposal);
    const parsedResponse = ContentPlanningProposalResponseSchema.parse({
      status: "ready" as const,
      work_item_id: workItemId,
      service_card_id: serviceCardId,
      planning_input_digest: binding.planning_input_digest,
      input_summary: {
        goal: "refresh_existing" as const,
        final_canonical_url: publicUrl,
        proposed_ia_location: null,
        service_label: proposal.service_label,
        inventory_status: "available" as const,
        content_inventory_status: "available" as const,
        acf_section_inventory_status: "available" as const,
        source_assessments: sources,
        source_fact_count: 1,
        source_fact_ids: ["source_fact_operat"],
        source_material_ids: [],
        gsc_query_rows: [],
        regulatory_profile_id: null,
        regulatory_profile_version: null,
        regulatory_requirement_ids: [],
        regulatory_source_fact_ids: [],
        regulatory_requirement_coverage: [],
        regulatory_review_candidates: [],
        evidence_id_count: 1,
        knowledge_card_count: 1,
        measurement_metrics: [],
        metric_comparisons: []
      },
      proposal: parsedProposal,
      planning_workspace: null,
      refresh_preparation_binding: binding,
      runtime: {
        status: "completed" as const,
        run_id: "codex_planning_operat",
        thread_id: "thread_planning_operat",
        turn_id: "turn_planning_operat",
        event_methods: ["turn/completed"],
        item_types: ["agentMessage"],
        external_call_attempted: false
      },
      blockers: [],
      safe_next_step: "Sprawdź plan przed przygotowaniem pełnego tekstu.",
      publish_ready: false as const
    });
    const parsedRevision = ContentDraftRevisionSchema.parse(revision);
    const parsedInitial = ContentInitialDraftResponseSchema.parse({
      status: "created" as const,
      work_item_id: workItemId,
      proposal_id: proposal.proposal_id,
      run_id: "codex_initial_operat",
      revision: parsedRevision,
      reuse_binding: null,
      runtime: {
        status: "completed" as const,
        run_id: "codex_initial_operat",
        thread_id: "thread_initial_operat",
        turn_id: "turn_initial_operat",
        event_methods: ["turn/completed"],
        item_types: ["agentMessage"],
        external_call_attempted: false
      },
      blockers: [],
      safe_next_step: "Przeczytaj pełną stronę przed decyzją człowieka.",
      publish_ready: false as const
    });

    expect(parsedResponse.refresh_preparation_binding).toEqual(binding);
    expect(parsedRevision.refresh_preparation_binding).toEqual(binding);
    if (parsedInitial.revision === null) throw new Error("expected created revision");
    expect(parsedInitial.revision.refresh_preparation_binding).toEqual(binding);
    expect(JSON.parse(JSON.stringify(parsedResponse))).toMatchObject({
      proposal: { refresh_preparation_binding: binding },
      refresh_preparation_binding: binding
    });
    expect(ContentPlanningProposalResponseSchema.safeParse({
      ...parsedResponse,
      refresh_preparation_binding: null
    }).success).toBe(false);
    expect(ContentPlanningProposalResponseSchema.safeParse({
      ...parsedResponse,
      refresh_preparation_binding: {
        ...binding,
        current_work_item_id: "content_work_item_foreign"
      }
    }).success).toBe(false);
    expect(ContentPlanningProposalResponseSchema.safeParse({
      ...parsedResponse,
      proposal: {
        ...parsedResponse.proposal,
        refresh_preparation_binding: null
      }
    }).success).toBe(false);
  });

  it("rejects partial authorization pairs and invalid nested bindings", () => {
    expect(ContentRefreshPreparationBindingSchema.parse(binding)).toEqual(binding);
    expect(ContentRefreshPreparationBindingSchema.safeParse({ ...binding, extra: true }).success)
      .toBe(false);
    expect(ContentRefreshPreparationBindingSchema.safeParse({
      ...binding,
      authorization_id: "content_refresh_preparation_authorization_wrong"
    }).success).toBe(false);
    expect(ContentPlanningProposalRequestSchema.safeParse({
      service_card_id: serviceCardId,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: binding.authorization_id
    }).success).toBe(false);
    expect(ContentPlanningProposalRequestSchema.safeParse({
      service_card_id: serviceCardId,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: null,
      expected_refresh_preparation_authorization_digest: null
    }).success).toBe(true);
    expect(ContentPlanningProposalRequestSchema.safeParse({
      service_card_id: serviceCardId,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: null,
      expected_refresh_preparation_authorization_digest: binding.authorization_digest
    }).success).toBe(false);
    expect(ContentPlanningProposalRequestSchema.safeParse({
      service_card_id: serviceCardId,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: binding.authorization_id,
      expected_refresh_preparation_authorization_digest: binding.authorization_digest,
      unexpected: true
    }).success).toBe(false);
    expect(ContentInitialDraftRequestSchema.safeParse({
      expected_proposal_id: proposal.proposal_id,
      expected_planning_digest: proposal.planning_digest,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: binding.authorization_id,
      expected_refresh_preparation_authorization_digest: binding.authorization_digest
    }).success).toBe(true);
    expect(ContentInitialDraftRequestSchema.safeParse({
      expected_proposal_id: proposal.proposal_id,
      expected_planning_digest: proposal.planning_digest,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: null,
      expected_refresh_preparation_authorization_digest: null
    }).success).toBe(true);
    expect(ContentInitialDraftRequestSchema.safeParse({
      expected_proposal_id: proposal.proposal_id,
      expected_planning_digest: proposal.planning_digest,
      expected_planning_input_digest: binding.planning_input_digest,
      requested_by: "wilku",
      refresh_preparation_authorization_id: binding.authorization_id,
      expected_refresh_preparation_authorization_digest: null
    }).success).toBe(false);
    expect(ContentInitialDraftResponseSchema.safeParse({
      status: "created",
      work_item_id: workItemId,
      proposal_id: proposal.proposal_id,
      run_id: "codex_initial_operat",
      revision: {
        ...revision,
        refresh_preparation_binding: {
          ...binding,
          authorization_digest: hex("9")
        }
      },
      reuse_binding: null,
      runtime: {
        status: "completed",
        run_id: "codex_initial_operat",
        thread_id: "thread_initial_operat",
        turn_id: "turn_initial_operat",
        event_methods: [],
        item_types: [],
        external_call_attempted: false
      },
      blockers: [],
      safe_next_step: "Sprawdź pełną stronę.",
      publish_ready: false
    }).success).toBe(false);
    expect(ContentDraftRevisionSchema.safeParse({
      ...revision,
      proposal_metadata: {
        ...revision.proposal_metadata,
        refresh_preparation_binding: null
      }
    }).success).toBe(false);
  });
});
