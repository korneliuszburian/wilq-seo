import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemPlanningProposal,
  getKnowledgeSourceMaterialReadiness,
  postContentWorkItemPlanningProposal
} from "../lib/api";
import {
  ContentPlanningGenerationPanel,
  planningSourceOutcomeLabels,
  planningSourceSummary
} from "./ContentPlanningGenerationPanel";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemPlanningProposal: vi.fn().mockResolvedValue({
    status: "not_generated",
    work_item_id: "work_item",
    proposal: null,
    blockers: [],
    safe_next_step: "Wybierz usługę.",
    publish_ready: false
  }),
  getKnowledgeSourceMaterialReadiness: vi.fn(),
  postContentWorkItemPlanningProposal: vi.fn()
}));

describe("ContentPlanningGenerationPanel", () => {
  it("summarizes used sources and excludes unbound GA4/Ads from the plan", () => {
    const summaryInput: Parameters<typeof planningSourceSummary>[0] = {
      source_assessments: [
        { source: "wordpress", status: "used", reason: "", landing_match_tiers: ["exact"], evidence_ids: [], knowledge_card_ids: [] },
        { source: "gsc", status: "used", reason: "", landing_match_tiers: ["exact"], evidence_ids: [], knowledge_card_ids: [] },
        { source: "ga4", status: "not_applicable", reason: "", landing_match_tiers: [], evidence_ids: [], knowledge_card_ids: [] },
        { source: "google_ads", status: "blocked", reason: "", landing_match_tiers: [], evidence_ids: [], knowledge_card_ids: [] }
      ],
      final_canonical_url: "https://ekologus.pl/bdo/",
      service_label: "BDO",
      inventory_status: "available",
      content_inventory_status: "available",
      source_fact_count: 0,
      source_fact_ids: [],
      source_material_ids: [],
      evidence_id_count: 0,
      knowledge_card_count: 0,
      measurement_metrics: [],
      metric_comparisons: []
    };
    const summary = planningSourceSummary(summaryInput);

    expect(summary).toContain("Źródła planu: 2/4 użyte · 2 z exact powiązaniem ze stroną.");
    expect(summary).toContain("GA4: nie dotyczy");
    expect(summary).toContain("Google Ads: zablokowane");
    expect(planningSourceOutcomeLabels(summaryInput.source_assessments)).toEqual([
      "WordPress: użyte · exact",
      "GSC: użyte · exact",
      "GA4: nie dotyczy",
      "Google Ads: zablokowane"
    ]);
  });

  it("renders exact page-scoped metric changes without inventing targets", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "not_generated",
      work_item_id: "work_item",
      proposal: null,
      blockers: [],
      input_summary: {
        final_canonical_url: "https://ekologus.pl/bdo/",
        service_label: "BDO",
        inventory_status: "available",
        content_inventory_status: "available",
        source_assessments: Array.from({ length: 10 }, (_, index) => ({
          source: ["wordpress", "service_profile", "gsc", "ga4", "google_ads", "ahrefs", "keyword_planner", "merchant", "localo", "social"][index],
          status: "used",
          reason: "",
          landing_match_tiers: ["exact"],
          evidence_ids: [],
          knowledge_card_ids: []
        })),
        source_fact_count: 0,
        source_fact_ids: [],
        source_material_ids: [],
        source_fact_previews: [{
          fact_id: "fact_bdo",
          summary: "Ekologus wspiera przedsiębiorców w obszarze BDO i sprawozdawczości.",
          source_connector: "public_site",
          evidence_ids: ["ev_bdo"],
          knowledge_card_ids: [],
          source_fact_ids: ["fact_bdo"],
          source_material_ids: ["KB_BDO"]
        }],
        evidence_id_count: 2,
        knowledge_card_count: 0,
        measurement_metrics: ["clicks"],
        metric_comparisons: [{
          source_connector: "google_search_console",
          status: "available",
          baseline_period: "2026-06-01/2026-06-28",
          comparison_period: "2026-06-29/2026-07-26",
          metric_names: ["clicks", "ctr"],
          baseline_values: { clicks: 12, ctr: 0.04 },
          comparison_values: { clicks: 19, ctr: 0.06 },
          evidence_ids: ["ev_gsc_1"],
          reason: ""
        }]
      },
      safe_next_step: "Wybierz usługę.",
      publish_ready: false
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId={null} workItemId="work_item" />
      </QueryClientProvider>
    );

    const comparisons = await screen.findByTestId("content-planning-metric-comparisons");
    expect(comparisons).toHaveTextContent("Google Search Console");
    expect(comparisons).toHaveTextContent("12 → 19");
    expect(comparisons).toHaveTextContent("2026-06-01/2026-06-28 → 2026-06-29/2026-07-26");
    expect(comparisons).not.toHaveTextContent("cel");
  });

  it("shows the redacted source fact that feeds the plan with lineage", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "not_generated",
      work_item_id: "work_item",
      proposal: null,
      blockers: [],
      input_summary: {
        final_canonical_url: "https://ekologus.pl/bdo/",
        service_label: "BDO",
        inventory_status: "available",
        source_assessments: [],
        source_fact_count: 1,
        source_fact_ids: ["fact_bdo"],
        source_material_ids: ["KB_BDO"],
        source_fact_previews: [{
          fact_id: "fact_bdo",
          summary: "Ekologus wspiera przedsiębiorców w obszarze BDO i sprawozdawczości.",
          source_connector: "public_site",
          evidence_ids: ["ev_bdo"],
          knowledge_card_ids: [],
          source_fact_ids: ["fact_bdo"],
          source_material_ids: ["KB_BDO"]
        }],
        evidence_id_count: 1,
        knowledge_card_count: 1,
        measurement_metrics: []
      }
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId={null} workItemId="work_item" />
      </QueryClientProvider>
    );
    const facts = await screen.findByTestId("content-planning-source-facts");
    expect(facts).toHaveTextContent("Ekologus wspiera przedsiębiorców");
    expect(facts).toHaveTextContent("1 materiał");
    expect(facts).toHaveTextContent("1 evidence");
  });

  it("shows the real corpus gate without blocking the planning view", async () => {
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "import_pending",
      total_count: 15,
      imported_count: 7,
      import_pending_count: 8,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
      pending_materials: [{
        source_id: "ekologus_material_kb001",
        file_name: "KB_001_EKO_OPIEKA.cleaned.md",
        title: "Eko-Opieka",
        kind: "knowledge_card",
        word_count: 166,
        digest_prefix: "4493485707a7d57b",
        privacy_class: "redacted_only",
        import_status: "import_pending",
        source_path: "materials_clean/approved/KB_001_EKO_OPIEKA.cleaned.md"
      }],
      blocker: "Zaimportowano 7 z 15 zatwierdzonych materiałów.",
      next_step: "Kontrolowany import po owner review."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId={null} workItemId="work_item" />
      </QueryClientProvider>
    );

    expect(
      await screen.findByTestId("content-material-readiness-warning")
    ).toHaveTextContent("7/15");
    expect(screen.getByText(/Zaimportowano 7 z 15 zatwierdzonych materiałów/)).toBeInTheDocument();
    expect(screen.getByText(/Kontrolowany import po owner review/)).toBeInTheDocument();
    expect(screen.getByText(/Czekają: Eko-Opieka/)).toBeInTheDocument();
  });

  it("does not generate from a recommendation before the marketer confirms the service", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "not_generated",
      work_item_id: "work_item",
      proposal: { service_selection_confirmed: false },
      blockers: [],
      safe_next_step: "Potwierdź usługę.",
      publish_ready: false
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId="service_card" workItemId="work_item" />
      </QueryClientProvider>
    );

    expect(
      await screen.findByTestId("content-planning-service-confirmation-gate")
    ).toHaveTextContent("Najpierw potwierdź usługę");
    expect(screen.queryByRole("button", { name: "Wygeneruj plan" })).not.toBeInTheDocument();
  });

  it("keeps retry available after a failed run with no persisted proposal", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "failed",
      work_item_id: "work_item",
      service_card_id: "service_card",
      planning_input_digest: "a".repeat(64),
      proposal: null,
      input_summary: {
        final_canonical_url: "https://ekologus.pl/bdo/",
        service_label: "BDO",
        inventory_status: "available",
        content_inventory_status: "available",
        source_assessments: [],
        source_fact_count: 0,
        source_fact_ids: [],
        source_material_ids: [],
        evidence_id_count: 0,
        knowledge_card_count: 0,
        measurement_metrics: []
      },
      blockers: [{
        code: "runtime_failed",
        label: "Codex nie zwrócił bezpiecznego planu",
        reason: "App-server nie zakończył turnu poprawnym ustrukturyzowanym wynikiem.",
        next_step: "Sprawdź runtime i rozpocznij nową próbę; WILQ nic nie zapisał.",
        source_codes: ["codex_response_stream_disconnected"]
      }],
      runtime: {
        status: "failed",
        run_id: "codex_content_planning_test",
        thread_id: null,
        turn_id: null,
        event_methods: ["error"],
        item_types: ["userMessage"],
        external_call_attempted: false
      },
      safe_next_step: "Sprawdź runtime i rozpocznij nową próbę; WILQ nic nie zapisał.",
      publish_ready: false
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "generating",
      work_item_id: "work_item",
      service_card_id: "service_card",
      planning_input_digest: "a".repeat(64),
      blockers: [],
      safe_next_step: "Poczekaj na plan.",
      publish_ready: false
    } as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId="service_card" workItemId="work_item" />
      </QueryClientProvider>
    );

    const retry = await screen.findByRole("button", { name: "Spróbuj ponownie" });
    expect(retry).toBeInTheDocument();
    expect(await screen.findByTestId("content-planning-runtime-run")).toHaveTextContent(
      "codex_content_planning_test"
    );
    expect(await screen.findByTestId("content-planning-blocker-trace")).toHaveTextContent(
      "codex_response_stream_disconnected"
    );
    await retry.click();
    expect(postContentWorkItemPlanningProposal).toHaveBeenCalledTimes(1);
  });

  it("shows page assets from the API-owned plan without offering a vendor write", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      status: "ready",
      work_item_id: "work_item",
      planning_input_digest: "a".repeat(64),
      proposal: {
        service_selection_confirmed: true,
        service_card_id: "service_card",
        generation_status: "codex_generated",
        proposal_id: "proposal_1",
        angle: "konkretny zakres współpracy",
        search_intent: "commercial",
        page_assets: {
          title: "Doradztwo środowiskowe | Ekologus",
          h1: "Doradztwo środowiskowe dla firm",
          lead: "Sprawdź zakres wsparcia dla swojej firmy.",
          meta_title: "Doradztwo środowiskowe | Ekologus",
          meta_description: "Poznaj zakres doradztwa środowiskowego.",
        },
        sections: [],
        faq: [],
        cta_blocks: [],
        internal_links: [],
        search_demand: { gsc_query_rows: [], ads_term_rows: [], keyword_planner_rows: [] },
      },
      blockers: [],
      safe_next_step: "Sprawdź plan.",
      publish_ready: false
    } as never);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValueOnce({
      status: "ready",
      total_count: 15,
      imported_count: 15,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: true,
      blocker: null,
      next_step: "Można planować."
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningGenerationPanel serviceCardId="service_card" workItemId="work_item" />
      </QueryClientProvider>
    );

    const assets = await screen.findByTestId("content-planning-page-assets");
    expect(assets).toHaveTextContent("Doradztwo środowiskowe | Ekologus");
    expect(assets).toHaveTextContent("Doradztwo środowiskowe dla firm");
    expect(assets).toHaveTextContent("bez zapisu do WordPress");
    expect(screen.queryByRole("button", { name: /WordPress/i })).not.toBeInTheDocument();
  });
});
