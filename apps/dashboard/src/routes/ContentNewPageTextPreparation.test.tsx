import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getContentNewPagePlanningProposal } from "../lib/api";
import { ContentNewPageTextPreparation } from "./ContentNewPageTextPreparation";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentNewPagePlanningProposal: vi.fn()
}));

afterEach(() => vi.clearAllMocks());

describe("ContentNewPageTextPreparation", () => {
  it("shows the exact brief inputs without inventing page-query history", async () => {
    vi.mocked(getContentNewPagePlanningProposal).mockResolvedValue({
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
          source_assessments: [
            { source: "service_profile", status: "used", reason: "Zatwierdzona usługa.", evidence_ids: [] },
            { source: "knowledge", status: "used", reason: "Przypisane materiały.", evidence_ids: [] },
            { source: "wordpress", status: "not_applicable", reason: "Brak istniejącej strony.", evidence_ids: [] },
            { source: "gsc", status: "missing", reason: "Nowa strona nie ma historii.", evidence_ids: [] },
            { source: "ga4", status: "blocked", reason: "Pomiar zacznie się po wdrożeniu.", evidence_ids: [] }
          ],
          source_fact_count: 2,
          source_fact_ids: [],
          source_material_ids: ["material_1"],
          evidence_id_count: 2,
          knowledge_card_count: 1,
          measurement_metrics: [],
          metric_comparisons: []
        },
        new_page_document_identity: { work_item_id: "new_page_work_item", proposed_ia_location: "/uslugi/bdo/" },
        blockers: [],
        safe_next_step: "Przygotuj tekst."
      },
      proposal_status: {
        proposal: {
          search_demand: {
            gsc_query_rows: [{ term: "historyczne zapytanie", period: "2026-07", impressions: 181, clicks: 4 }]
          }
        }
      }
    } as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ContentNewPageTextPreparation briefId="brief_1" /></QueryClientProvider>);

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    const evidence = screen.getByTestId("content-planning-evidence");
    expect(evidence).toHaveTextContent("kontekst usługi");
    expect(evidence).toHaveTextContent("baza wiedzy");
    expect(evidence).toHaveTextContent("To źródło nie dotyczy tej pracy. Brak istniejącej strony.");
    expect(evidence).toHaveTextContent("Brak danych. Nowa strona nie ma historii.");
    expect(evidence).toHaveTextContent("Źródło jest zablokowane. Pomiar zacznie się po wdrożeniu.");
    expect(evidence).toHaveTextContent("Nowa strona nie ma własnej historii GSC");
    expect(evidence).not.toHaveTextContent("historyczne zapytanie");
    expect(evidence).not.toHaveTextContent("181 wyświetleń");
    expect(evidence).not.toHaveTextContent("niewystarczająco dokładne lub świeże");
  });
});
