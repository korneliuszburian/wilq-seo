import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ContentNewPagePlanningProposalWorkspaceSchema } from "@wilq/shared-schemas";

import { getContentNewPagePlanningProposal } from "../lib/api";
import { ContentNewPageTextPreparation } from "./ContentNewPageTextPreparation";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentNewPagePlanningProposal: vi.fn()
}));

afterEach(() => vi.clearAllMocks());

describe("ContentNewPageTextPreparation", () => {
  it("shows the exact brief inputs without inventing page-query history", async () => {
    const identity = {
      work_item_id: "new_page_work_item", work_kind: "new_page", brief_id: "brief_1",
      brief_digest: "b".repeat(64), foundation_id: "foundation_1", service_card_id: "service_1",
      service_card_digest: "c".repeat(64), proposed_ia_location: "/uslugi/bdo/",
      public_source_status: "not_applicable", public_source_url: null, public_source_evidence_ids: [],
      document_status: "not_created", public_deployment_status: "not_confirmed", public_deployment_id: null
    } as const;
    const assessments = ["wordpress", "service_profile", "gsc", "ga4", "google_ads", "ahrefs", "keyword_planner", "merchant", "localo", "social"].map((source) => ({
      source, status: source === "service_profile" ? "used" : source === "wordpress" ? "not_applicable" : source === "gsc" ? "missing" : source === "ga4" ? "blocked" : "not_applicable",
      reason: source === "service_profile" ? "Zatwierdzona karta usługi." : source === "wordpress" ? "Brak istniejącej strony." : source === "gsc" ? "Nowa strona nie ma historii." : source === "ga4" ? "Pomiar zacznie się po wdrożeniu." : source === "social" ? "To źródło nie dotyczy tej pracy." : "Jawna ocena źródła.", evidence_ids: []
    }));
    const fixture = ContentNewPagePlanningProposalWorkspaceSchema.parse({
      response_type: "content_new_page_planning_proposal_workspace", contract_version: "content_new_page_planning_proposal_workspace_v1", brief_id: "brief_1",
      readiness: {
        status: "ready",
        work_item_id: "new_page_work_item",
        planning_input_digest: "a".repeat(64),
        input_summary: {
          goal: "new_page",
          final_canonical_url: null,
          proposed_ia_location: "/uslugi/bdo/",
          service_label: "BDO",
          inventory_status: "not_applicable",
          content_inventory_status: "not_applicable",
          acf_section_inventory_status: "not_applicable",
          source_assessments: assessments,
          source_fact_count: 2,
          source_fact_ids: [],
          source_material_ids: ["material_1"],
          evidence_id_count: 2,
          knowledge_card_count: 1,
          measurement_metrics: [],
          metric_comparisons: []
        },
        new_page_document_identity: identity,
        blockers: [],
        safe_next_step: "Przygotuj tekst."
      },
      proposal_status: {
        status: "ready", work_item_id: "new_page_work_item", service_card_id: "service_1", planning_input_digest: "a".repeat(64),
        input_summary: { goal: "new_page", final_canonical_url: null, proposed_ia_location: "/uslugi/bdo/", service_label: "BDO", inventory_status: "not_applicable", content_inventory_status: "not_applicable", acf_section_inventory_status: "not_applicable", source_assessments: assessments, source_fact_count: 2, source_fact_ids: [], source_material_ids: ["material_1"], evidence_id_count: 2, knowledge_card_count: 1, measurement_metrics: [], metric_comparisons: [] },
        proposal: {
          work_item_id: "new_page_work_item", planning_digest: "d".repeat(64), proposal_id: "proposal_1", generation_status: "codex_generated", planning_input_digest: "a".repeat(64), goal: "new_page", final_canonical_url: null, proposed_ia_location: "/uslugi/bdo/", new_page_document_identity: identity, service_card_id: "service_1", service_label: "BDO", target_reader: "firma", buyer_problem: "problem", buyer_trigger: "potrzeba", search_intent: "informacyjna", cta_direction: "kontakt", internal_link_directions: [], sections: [{ heading: "Zakres", purpose: "Pomoc", inventory_disposition: "create", inventory_section_id: null, inventory_heading: null, evidence_ids: [] }], evidence_ids: [], source_connectors: [],
          search_demand: {
            status: "available", gsc_query_rows: [{ source_kind: "gsc_query", source_connector: "google_search_console", term: "historyczne zapytanie", page: "https://example.test", landing_match_tiers: [], service_card_id: null, alignment_basis: "gsc_exact_page", review_required: true, section_headings: [], section_mapping_status: "page_only", period: "2026-07", freshness: "fresh", collected_at: null, evidence_ids: ["ev_1"], impressions: 181, clicks: 4, ctr: null, average_position: null, average_monthly_searches: null }], ads_term_rows: [], keyword_planner_rows: [], source_connectors: ["google_search_console"], evidence_ids: ["ev_1"], optional_ads_status: "not_exactly_mapped", safe_next_step: "Sprawdź."
          }
        }, runtime: { status: "completed", thread_id: null, turn_id: null, external_call_attempted: false }, blockers: [], safe_next_step: "Przygotuj tekst.", publish_ready: false
      }
    });
    vi.mocked(getContentNewPagePlanningProposal).mockResolvedValue(fixture);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ContentNewPageTextPreparation briefId="brief_1" /></QueryClientProvider>);

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    const evidence = screen.getByTestId("content-planning-evidence");
    expect(evidence).toHaveTextContent("kontekst usługi");
    expect(evidence).toHaveTextContent("Wykorzystane. Zatwierdzona karta usługi.");
    expect(evidence).toHaveTextContent("media społecznościowe");
    expect(evidence).toHaveTextContent("To źródło nie dotyczy tej pracy.");
    expect(evidence).not.toHaveTextContent("social:");
    expect(evidence).toHaveTextContent("To źródło nie dotyczy tej pracy. Brak istniejącej strony.");
    expect(evidence).toHaveTextContent("Brak danych. Nowa strona nie ma historii.");
    expect(evidence).toHaveTextContent("Źródło jest zablokowane. Pomiar zacznie się po wdrożeniu.");
    expect(evidence).toHaveTextContent("Nowa strona nie ma własnej historii GSC");
    expect(evidence).not.toHaveTextContent("historyczne zapytanie");
    expect(evidence).not.toHaveTextContent("2026-07");
    expect(evidence).not.toHaveTextContent("181 wyświetleń");
    expect(evidence).not.toHaveTextContent("4 kliknięć");
    expect(evidence).not.toHaveTextContent("niewystarczająco dokładne lub świeże");
  });
});
