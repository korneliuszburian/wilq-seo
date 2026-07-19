import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemPlanningProposal,
  getKnowledgeSourceMaterialReadiness
} from "../lib/api";
import {
  ContentPlanningGenerationPanel,
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
  getKnowledgeSourceMaterialReadiness: vi.fn()
}));

describe("ContentPlanningGenerationPanel", () => {
  it("summarizes used sources and excludes unbound GA4/Ads from the plan", () => {
    const summary = planningSourceSummary({
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
      measurement_metrics: []
    });

    expect(summary).toContain("Źródła planu: 2/4 użyte · 2 z exact powiązaniem ze stroną.");
    expect(summary).toContain("GA4: nie dotyczy");
    expect(summary).toContain("Google Ads: zablokowane");
  });

  it("shows the real corpus gate without blocking the planning view", async () => {
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "import_pending",
      total_count: 15,
      imported_count: 7,
      import_pending_count: 8,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
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
});
