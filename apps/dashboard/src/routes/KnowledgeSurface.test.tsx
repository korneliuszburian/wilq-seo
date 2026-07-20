import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { KnowledgeOperatingMapResponse } from "../lib/api";
import { getKnowledgeCards, getKnowledgeOperatingMap, getKnowledgePlaybooks, getKnowledgeSourceFacts, getKnowledgeSourceMaterialReadiness, getKnowledgeSourceMaterials } from "../lib/api";
import { approvedKnowledgeFactCount, GenericSurface } from "./GenericSurface";

vi.mock("../lib/api", () => ({
  getConnectors: vi.fn(),
  getConnectorRefreshRun: vi.fn(),
  getKnowledgeOperatingMap: vi.fn(),
  getKnowledgeCards: vi.fn(),
  getKnowledgePlaybooks: vi.fn(),
  getKnowledgeSourceFacts: vi.fn(),
  getKnowledgeSourceMaterials: vi.fn(),
  getKnowledgeSourceMaterialReadiness: vi.fn(),
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

  it("counts only source facts eligible for generation", () => {
    expect(
      approvedKnowledgeFactCount([
        { generation_status: "eligible" },
        { generation_status: "blocked_review_required" },
        { generation_status: "eligible" }
      ])
    ).toBe(2);
    expect(approvedKnowledgeFactCount(undefined)).toBe(0);
  });

  it("renders the evidence-backed knowledge decision and keeps details behind disclosure", async () => {
    vi.mocked(getKnowledgeOperatingMap).mockResolvedValue(operatingMap);
    vi.mocked(getKnowledgeCards).mockResolvedValue([]);
    vi.mocked(getKnowledgePlaybooks).mockResolvedValue([]);
    vi.mocked(getKnowledgeSourceFacts).mockResolvedValue([]);
    vi.mocked(getKnowledgeSourceMaterials).mockResolvedValue([
      {
        source_id: "ekologus_material_kb014",
        file_name: "KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md",
        title: "Styl marki i język Ekologus",
        kind: "policy",
        word_count: 306,
        digest_prefix: "8186c09a4f715e64",
        privacy_class: "redacted_only",
        import_status: "import_pending",
        source_path: "materials_clean/approved/KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md"
      }
    ]);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "import_pending",
      total_count: 15,
      imported_count: 0,
      import_pending_count: 15,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
      pending_materials: [{
        source_id: "ekologus_material_kb014",
        file_name: "KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md",
        title: "Styl marki i język Ekologus",
        kind: "policy",
        word_count: 306,
        digest_prefix: "8186c09a4f715e64",
        privacy_class: "redacted_only",
        import_status: "import_pending",
        source_path: "materials_clean/approved/KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md"
      }],
      blocker: "Korpus oczekuje na import.",
      next_step: "Zatwierdź excerpty."
    });
    renderKnowledge();

    expect(await screen.findByRole("heading", { name: "Źródła i wiedza" })).toBeInTheDocument();
    expect(screen.getByText("Najbliższy krok źródłowy")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kolejka review materiałów źródłowych" })).toBeInTheDocument();
    expect(await screen.findByText("Wymaga review excerptu")).toBeInTheDocument();
    expect(await screen.findByText("KB_014_STYL_MARKI_JEZYK_EKOLOGUS.cleaned.md")).toBeInTheDocument();
    expect((await screen.findAllByText("Doprowadź 1 materiałów Ekologusa do redakcji i review")).length).toBeGreaterThan(0);
    expect(screen.getByText(/1 twierdzeń wymaga blokady/)).toBeInTheDocument();
    expect(screen.queryByText("binding_ads_review")).not.toBeInTheDocument();
    expect(screen.queryByText("ROAS")).not.toBeInTheDocument();
    expect(screen.getByText("1 materiałów w manifeście Ekologusa")).toBeInTheDocument();
    expect(screen.getByText("Korpus źródłowy: zablokowany")).toBeInTheDocument();
    expect(screen.getByText("Czekają konkretne materiały: Styl marki i język Ekologus")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Zasady pracy z wiedzą" }));
    expect(screen.getByText("Co blokuje produkcję treści")).toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
  });

  it("keeps the knowledge layout useful while the operating map is loading", async () => {
    vi.mocked(getKnowledgeOperatingMap).mockReturnValue(new Promise(() => {}));
    vi.mocked(getKnowledgeSourceFacts).mockReturnValue(new Promise(() => {}));
    vi.mocked(getKnowledgeSourceMaterials).mockReturnValue(new Promise(() => {}));
    renderKnowledge();

    expect(await screen.findByRole("heading", { name: "Źródła i wiedza" })).toBeInTheDocument();
    expect(screen.getByText("Najbliższy krok źródłowy")).toBeInTheDocument();
    expect(screen.getAllByText("Ładowanie stanu WILQ").length).toBeGreaterThan(0);
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
  });

  it("does not substitute operational cards when the source manifest is empty", async () => {
    vi.mocked(getKnowledgeOperatingMap).mockResolvedValue(operatingMap);
    vi.mocked(getKnowledgeCards).mockResolvedValue([
      { id: "card_fake", title: "Nie jest źródłem", display_title: "Nie jest źródłem", card_type: "service", card_type_label: "Karta", source_type: "playbook", source_type_label: "Playbook" } as never
    ]);
    vi.mocked(getKnowledgePlaybooks).mockResolvedValue([]);
    vi.mocked(getKnowledgeSourceFacts).mockResolvedValue([]);
    vi.mocked(getKnowledgeSourceMaterials).mockResolvedValue([]);
    vi.mocked(getKnowledgeSourceMaterialReadiness).mockResolvedValue({
      status: "ready",
      total_count: 0,
      imported_count: 0,
      import_pending_count: 0,
      excerpt_review_required_count: 0,
      ready_for_generation: false,
      next_step: "Dodaj zatwierdzone materiały."
    });
    renderKnowledge();

    expect(await screen.findByText("Brak manifestu materiałów źródłowych. Nie zastępujemy go kartami operacyjnymi.")).toBeInTheDocument();
    expect(screen.queryByText("Nie jest źródłem")).not.toBeInTheDocument();
  });
});
