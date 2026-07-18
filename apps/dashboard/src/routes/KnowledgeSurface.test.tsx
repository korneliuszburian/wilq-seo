import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { KnowledgeOperatingMapResponse } from "../lib/api";
import { getKnowledgeCards, getKnowledgeOperatingMap, getKnowledgePlaybooks } from "../lib/api";
import { GenericSurface } from "./GenericSurface";

vi.mock("../lib/api", () => ({
  getConnectors: vi.fn(),
  getConnectorRefreshRun: vi.fn(),
  getKnowledgeOperatingMap: vi.fn(),
  getKnowledgeCards: vi.fn(),
  getKnowledgePlaybooks: vi.fn(),
  refreshConnector: vi.fn(),
  getWorkflowRuns: vi.fn(),
  getWorkflows: vi.fn()
}));

const operatingMap: KnowledgeOperatingMapResponse = {
  generated_at: "2026-07-13T07:00:00Z",
  source_card_count: 1,
  playbook_count: 1,
  expert_rule_count: 1,
  binding_count: 1,
  blocked_binding_summary_label: "1 blokada",
  missing_contract_summary_label: "1 brakujący kontrakt",
  blocked_claim_count_summary_label: "1 zablokowane twierdzenie",
  bindings: [
    {
      id: "binding_ads_review",
      title: "Sprawdź pomiar przed decyzją Ads",
      route: "/ads-doctor",
      route_label: "Reklamy i pomiar",
      skill_id: "wilq-ads-doctor",
      summary: "Karta wymaga decyzji człowieka przed użyciem.",
      next_step: "Zweryfikuj dowody i blokady.",
      source_connectors: ["google_ads"],
      source_connector_labels: ["Google Ads"],
      source_connector_summary_label: "Google Ads",
      evidence_ids: ["ev_ads"],
      evidence_summary_label: "1 dowód",
      action_ids: [],
      action_summary_label: "Brak akcji do sprawdzenia",
      metric_tiles: {},
      knowledge_card_ids: ["card_ads"],
      playbook_ids: ["playbook_ads"],
      expert_rule_ids: ["rule_ads"],
      knowledge_summary_label: "1 karta wiedzy",
      required_evidence: ["search_terms"],
      required_evidence_summary_label: "search terms",
      missing_contracts: ["conversion"],
      missing_contract_labels: ["konwersje"],
      missing_contract_summary_label: "1 brakujący kontrakt",
      missing_contract_detail_label: "konwersje",
      has_missing_contracts: true,
      blocked_claims: ["roas"],
      blocked_claim_labels: ["ROAS"],
      blocked_claim_summary_label: "1 zablokowane twierdzenie",
      blocked_claim_count_summary_label: "1 zablokowane twierdzenie",
      has_blocked_claims: true,
      source_lineage: ["ev_ads"],
      source_lineage_summary_label: "1 źródło",
      risk: "medium",
      risk_label: "średnie ryzyko",
      status: "planned",
      status_label: "wymaga review"
    }
  ]
};

function renderKnowledge() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <GenericSurface routeName="/knowledge" />
    </QueryClientProvider>
  );
}

describe("KnowledgeSurface", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders the evidence-backed knowledge decision and keeps details behind disclosure", async () => {
    vi.mocked(getKnowledgeOperatingMap).mockResolvedValue(operatingMap);
    vi.mocked(getKnowledgeCards).mockResolvedValue([]);
    vi.mocked(getKnowledgePlaybooks).mockResolvedValue([]);
    renderKnowledge();

    expect(await screen.findByRole("heading", { name: "Wiedza" })).toBeInTheDocument();
    expect(screen.getByText("Najbliższa wiedza do sprawdzenia")).toBeInTheDocument();
    expect((await screen.findAllByText("Sprawdź kartę: Sprawdź pomiar przed decyzją Ads")).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 twierdzeń wymaga blokady/)).toBeInTheDocument();
    expect(screen.queryByText("binding_ads_review")).not.toBeInTheDocument();
    expect(screen.getByText("ROAS")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Zasady pracy z wiedzą" }));
    expect(screen.getByText("Co blokuje produkcję treści")).toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
  });

  it("keeps the knowledge layout useful while the operating map is loading", async () => {
    vi.mocked(getKnowledgeOperatingMap).mockReturnValue(new Promise(() => {}));
    renderKnowledge();

    expect(await screen.findByRole("heading", { name: "Wiedza" })).toBeInTheDocument();
    expect(screen.getByText("Najbliższa wiedza do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("Ładowanie stanu WILQ")).toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
  });
});
