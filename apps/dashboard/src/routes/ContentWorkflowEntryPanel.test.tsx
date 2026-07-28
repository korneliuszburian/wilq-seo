import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createContentNewPageFoundation, createContentNewPagePlanningProposal, getContentNewPageBriefWorkspace, getContentNewPageCanonicalDocument, getContentNewPagePlanningProposal, type ContentNewPageBriefWorkspace, type ContentNewPageCanonicalDocumentWorkspace, type ContentNewPagePlanningProposalWorkspace, type ContentWorkflowEntryResponse } from "../lib/api";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, createContentNewPageFoundation: vi.fn(), createContentNewPagePlanningProposal: vi.fn(), getContentNewPageBriefWorkspace: vi.fn(), getContentNewPageCanonicalDocument: vi.fn(), getContentNewPagePlanningProposal: vi.fn() };
});

const entry: ContentWorkflowEntryResponse = {
  response_type: "content_workflow_entry",
  refresh_existing: {
    kind: "refresh_existing",
    label: "Odśwież istniejącą stronę",
    description: "Sprawdź obecną treść i przygotuj jej nową wersję.",
    route: "refresh_existing"
  },
  new_page: {
    kind: "new_page",
    label: "Utwórz nową stronę",
    description: "Zacznij od briefu nowej strony, bez wymaganego starego adresu.",
    route: "new_page"
  },
  recommendations: [{
    work_item_id: "content_work_item_bdo",
    title: "BDO dla firm",
    url: "https://www.ekologus.pl/bdo/",
    reason: "Strona wymaga sprawdzenia na podstawie danych GSC.",
    facts: [{ label: "Wyświetlenia GSC", value: "107" }]
  }],
  search_query: null,
  search_results: [],
  browse_inventory_label: "Przeglądaj cały serwis"
};

function renderEntry(overrides: Partial<ComponentProps<typeof ContentWorkflowEntryPanel>> = {}) {
  const props: ComponentProps<typeof ContentWorkflowEntryPanel> = {
    entry,
    inventory: null,
    browseInventory: false,
    newPageOpen: false,
    newPageId: null,
    onBrowseInventory: vi.fn(),
    onCloseSecondaryView: vi.fn(),
    onOpenNewPage: vi.fn(),
    onNewPageBriefSaved: vi.fn(),
    onSelectWorkItem: vi.fn(),
    ...overrides
  };
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ContentWorkflowEntryPanel {...props} />
    </QueryClientProvider>
  );
  return props;
}

describe("ContentWorkflowEntryPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("starts with marketer intent and only API-provided facts", () => {
    const props = renderEntry();

    expect(screen.getByRole("heading", { name: "Co chcesz zrobić?" })).toBeInTheDocument();
    expect(screen.getAllByText("Odśwież istniejącą stronę")).toHaveLength(2);
    expect(screen.getByText("Utwórz nową stronę")).toBeInTheDocument();
    expect(screen.getByText("Wyświetlenia GSC")).toBeInTheDocument();
    expect(screen.queryByText(/808 adresów/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /otwórz stronę/i }));
    expect(props.onSelectWorkItem).toHaveBeenCalledWith("content_work_item_bdo");
  });

  it("keeps the catalog and new-page brief behind explicit choices", () => {
    const props = renderEntry();

    fireEvent.click(screen.getByRole("button", { name: /przeglądaj cały serwis/i }));
    expect(props.onBrowseInventory).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: /zacznij od briefu/i }));
    expect(props.onOpenNewPage).toHaveBeenCalledOnce();
  });

  it("shows every saved brief assumption and catalog evidence for no direct coverage", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace());

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_no_conflict" });

    expect(await screen.findByText("Audyt środowiskowy dla inwestycji")).toBeInTheDocument();
    expect(screen.getByText("Intencja wyszukiwania")).toBeInTheDocument();
    expect(screen.getByText("audyt środowiskowy dla inwestycji")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Sprawdzone strony i dowody"));
    expect(screen.getByText("Dowody sprawdzonego katalogu: ev_wp_other")).toBeInTheDocument();
  });

  it("binds an explicit service card to the exact brief and overlap read", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace());
    vi.mocked(createContentNewPageFoundation).mockResolvedValue({
      status: "created",
      foundation: null,
      reason: "Podstawa zapisana.",
      safe_next_step: "Przygotuj plan dokumentu w kolejnym etapie workflow."
    });

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_no_conflict" });

    await screen.findByText("Podstawa planowania");
    fireEvent.change(screen.getByLabelText("Karta usługi"), { target: { value: "service_environment" } });
    fireEvent.change(screen.getByLabelText("Potwierdza"), { target: { value: "Wilku" } });
    fireEvent.click(screen.getByRole("button", { name: "Zapisz podstawę planowania" }));

    await waitFor(() => expect(createContentNewPageFoundation).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_brief_digest: "a".repeat(64),
      expected_overlap_digest: "b".repeat(64),
      service_card_id: "service_environment",
      confirmed_by: "Wilku"
    }));
  });

  it("shows exact new-page readiness and generates a plan only after the marketer chooses the next step", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, {
      foundation: {
        foundation_id: "content_new_page_foundation_test",
        work_item_id: "content_work_item_new_page_test",
        brief_id: "content_new_page_brief_test",
        brief_digest: "a".repeat(64),
        overlap_digest: "b".repeat(64),
        overlap_evidence_ids: ["ev_wp_other"],
        service_card_id: "service_environment",
        service_card_digest: "c".repeat(64),
        service_label: "Obsługa środowiskowa",
        service_evidence_ids: ["ev_service"],
        confirmed_by: "Wilku",
        created_at: "2026-07-28T00:00:00Z"
      }
    }));
    vi.mocked(getContentNewPagePlanningProposal).mockResolvedValue(newPagePlanningWorkspace());
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(canonicalDocumentWorkspace());
    vi.mocked(createContentNewPagePlanningProposal).mockResolvedValue(newPagePlanningWorkspace({ proposal_status: { ...newPagePlanningWorkspace().proposal_status!, status: "generating", safe_next_step: "Plan jest przygotowywany." } }));

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-planning-ready")).toBeInTheDocument();
    expect(screen.getByText(/nie przypisuje tej nowej stronie starego URL-a/i)).toBeInTheDocument();
    expect(getContentNewPagePlanningProposal).toHaveBeenCalledWith("content_new_page_brief_test");
    expect(await screen.findByTestId("new-page-canonical-document")).toBeInTheDocument();
    expect(screen.getByText("Nie dotyczy — to nowa strona.")).toBeInTheDocument();
    expect(getContentNewPageCanonicalDocument).toHaveBeenCalledWith("content_new_page_brief_test");
    expect(createContentNewPagePlanningProposal).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Przygotuj plan" }));

    await waitFor(() => expect(createContentNewPagePlanningProposal).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_planning_input_digest: "d".repeat(64),
      requested_by: "Wilku"
    }));
  });

  it("shows the candidate, matching basis, and evidence when a person must decide", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({
      disposition: "human_decision_required",
      label: "Pokrycie wymaga decyzji człowieka",
      candidates: [{
        title: "Audyt środowiskowy dla inwestycji",
        url: "https://www.ekologus.pl/audyt-srodowiskowy/",
        match_kind: "shared_intent",
        evidence_ids: ["ev_wp_audit"]
      }],
      evidence_ids: ["ev_wp_audit"]
    }));

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_human_decision" });

    expect(await screen.findByText("Pokrycie wymaga decyzji człowieka")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Sprawdzone strony i dowody"));
    expect(screen.getByText("Podstawa dopasowania: wspólna intencja wyszukiwania.")).toBeInTheDocument();
    expect(screen.getByText("Dowody: ev_wp_audit")).toBeInTheDocument();
  });

  it("does not describe an unevidenced human-decision guard as no direct coverage", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({
      disposition: "human_decision_required",
      label: "Nie można jeszcze ocenić pokrycia serwisu",
      candidates: [],
      evidence_ids: []
    }));

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_missing_evidence" });

    expect(await screen.findByText("Nie można jeszcze ocenić pokrycia serwisu")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Sprawdzone strony i dowody"));
    expect(screen.getByText("Nie ma potwierdzonych danych pozwalających ocenić pokrycie.")).toBeInTheDocument();
    expect(screen.queryByText("Nie znaleziono strony z bezpośrednim pokryciem. Poniżej są dowody z katalogu sprawdzonego dla tego briefu.")).not.toBeInTheDocument();
  });
});

function canonicalDocumentWorkspace(): ContentNewPageCanonicalDocumentWorkspace {
  return {
    response_type: "content_new_page_canonical_document",
    contract_version: "content_new_page_canonical_document_v2",
    status: "ready_for_document",
    work_item_id: "content_work_item_new_page_test",
    brief_id: "content_new_page_brief_test",
    brief_digest: "a".repeat(64),
    foundation_id: "content_new_page_foundation_test",
    service_card_id: "service_environment",
    service_card_digest: "c".repeat(64),
    proposal_id: "content_planning_proposal_test",
    planning_digest: "b".repeat(64),
    planning_input_digest: "d".repeat(64),
    plan_review: null,
    title: "Audyt środowiskowy dla inwestycji",
    proposed_ia_location: "Usługi → Audyt środowiskowy",
    outline: [],
    document_status: "not_created",
    canonical_revision: null,
    revision_review: null,
    assigned_source_material_ids: [],
    assigned_knowledge_card_ids: [],
    public_source_status: "not_applicable",
    public_source_url: null,
    public_deployment_status: "not_confirmed",
    safe_next_step: "Przygotuj pierwszą immutable rewizję."
  };
}

function savedBriefWorkspace(
  overlap: Partial<ContentNewPageBriefWorkspace["overlap_guard"]> = {},
  workspaceOverrides: Partial<ContentNewPageBriefWorkspace> = {}
): ContentNewPageBriefWorkspace {
  return {
    response_type: "content_new_page_brief_workspace",
    contract_version: "content_new_page_brief_workspace_v2",
    brief: {
      brief_id: "content_new_page_brief_test",
      brief_digest: "a".repeat(64),
      created_at: "2026-07-23T00:00:00Z",
      work_kind: "new_page",
      title: "Audyt środowiskowy dla inwestycji",
      purpose: "Pomóc inwestorowi przygotować audyt środowiskowy.",
      service: "Audyt środowiskowy",
      audience: "Inwestor przygotowujący przedsięwzięcie",
      search_intent: "audyt środowiskowy dla inwestycji",
      proposed_ia_location: "Usługi → Dokumentacja środowiskowa"
    },
    overlap_guard: {
      disposition: "no_conflict",
      label: "Nie znaleziono bezpośredniego pokrycia",
      reason: "Aktualny katalog nie pokazuje strony z tym samym tytułem.",
      caveat: "To nie jest dowód braku wszystkich możliwych duplikatów.",
      evidence_ids: ["ev_wp_other"],
      candidates: [],
      ...overlap
    },
    overlap_digest: "b".repeat(64),
    service_options: [{
      service_card_id: "service_environment",
      label: "Obsługa środowiskowa",
      summary: "Zatwierdzona karta usługi.",
      evidence_ids: ["ev_service"]
    }],
    foundation: null,
    review_status: "blocked",
    review_reason: "Brief nie jest jeszcze dokumentem do review.",
    next_action_label: "Przygotowanie dokumentu zostanie udostępnione w następnym etapie",
    ...workspaceOverrides
  };
}

function newPagePlanningWorkspace(
  overrides: Partial<ContentNewPagePlanningProposalWorkspace> = {}
): ContentNewPagePlanningProposalWorkspace {
  const sources = ["wordpress", "service_profile", "gsc", "ga4", "google_ads", "ahrefs", "keyword_planner", "merchant", "localo", "social"] as const;
  return {
    response_type: "content_new_page_planning_proposal_workspace",
    contract_version: "content_new_page_planning_proposal_workspace_v1",
    brief_id: "content_new_page_brief_test",
    readiness: {
      status: "ready",
      work_item_id: "content_work_item_new_page_test",
      planning_input_digest: "d".repeat(64),
      new_page_document_identity: {
        work_item_id: "content_work_item_new_page_test",
        work_kind: "new_page",
        brief_id: "content_new_page_brief_test",
        brief_digest: "a".repeat(64),
        foundation_id: "content_new_page_foundation_test",
        service_card_id: "service_environment",
        service_card_digest: "c".repeat(64),
        proposed_ia_location: "Usługi → Dokumentacja środowiskowa",
        public_source_status: "not_applicable",
        public_source_url: null,
        public_source_evidence_ids: [],
        document_status: "not_created",
        public_deployment_status: "not_confirmed",
        public_deployment_id: null
      },
      input_summary: {
        goal: "new_page",
        final_canonical_url: null,
        proposed_ia_location: "Usługi → Dokumentacja środowiskowa",
        service_label: "Obsługa środowiskowa",
        inventory_status: "not_applicable",
        content_inventory_status: "not_applicable",
        acf_section_inventory_status: "not_applicable",
        source_assessments: sources.map((source) => ({ source, status: "not_applicable", reason: "Nie dotyczy nowej strony.", landing_match_tiers: [], evidence_ids: [], knowledge_card_ids: [] })),
        source_fact_count: 1,
        source_fact_ids: ["fact_service"],
        source_material_ids: [],
        evidence_id_count: 1,
        knowledge_card_count: 1,
        measurement_metrics: [],
        metric_comparisons: []
      },
      blockers: [],
      safe_next_step: "Przygotuj propozycję planu."
    },
    proposal_status: {
      status: "not_generated",
      work_item_id: "content_work_item_new_page_test",
      service_card_id: "service_environment",
      planning_input_digest: "d".repeat(64),
      input_summary: {
        goal: "new_page",
        final_canonical_url: null,
        proposed_ia_location: "Usługi → Dokumentacja środowiskowa",
        service_label: "Obsługa środowiskowa",
        inventory_status: "not_applicable",
        content_inventory_status: "not_applicable",
        acf_section_inventory_status: "not_applicable",
        source_assessments: sources.map((source) => ({ source, status: "not_applicable", reason: "Nie dotyczy nowej strony.", landing_match_tiers: [], evidence_ids: [], knowledge_card_ids: [] })),
        source_fact_count: 1,
        source_fact_ids: ["fact_service"],
        source_material_ids: [],
        evidence_id_count: 1,
        knowledge_card_count: 1,
        measurement_metrics: [],
        metric_comparisons: []
      },
      retry_after_seconds: null,
      proposal: null,
      runtime: { status: "not_started", run_id: null, thread_id: null, turn_id: null, event_methods: [], item_types: [], external_call_attempted: false },
      blockers: [],
      safe_next_step: "Przygotuj propozycję planu.",
      publish_ready: false
    },
    ...overrides
  };
}
