import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createContentNewPageDeliveryAction, createContentNewPageFoundation, createContentNewPageInitialDraft, createContentNewPagePlanningProposal, getContentNewPageBriefWorkspace, getContentNewPageCanonicalDocument, getContentNewPageDeliveryReadiness, getContentNewPagePlanningProposal, getContentNewPageTopicRecommendations, refreshConnector, reviewContentNewPageRevision, type ContentDiagnosticsResponse, type ContentNewPageBriefWorkspace, type ContentNewPageCanonicalDocumentWorkspace, type ContentNewPagePlanningProposalWorkspace, type ContentWorkflowEntryResponse } from "../lib/api";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, createContentNewPageDeliveryAction: vi.fn(), createContentNewPageFoundation: vi.fn(), createContentNewPageInitialDraft: vi.fn(), createContentNewPagePlanningProposal: vi.fn(), getContentNewPageBriefWorkspace: vi.fn(), getContentNewPageCanonicalDocument: vi.fn(), getContentNewPageDeliveryReadiness: vi.fn(), getContentNewPagePlanningProposal: vi.fn(), getContentNewPageTopicRecommendations: vi.fn(), refreshConnector: vi.fn(), reviewContentNewPageRevision: vi.fn() };
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
    diagnostics: null,
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
  beforeEach(() => {
    vi.mocked(getContentNewPageTopicRecommendations).mockResolvedValue({
      response_type: "content_new_page_topic_recommendations",
      contract_version: "content_new_page_topic_recommendations_v1",
      status: "no_qualified_topics",
      title: "Brak bezpiecznej rekomendacji tematu",
      reason: "Brak pełnego potwierdzenia.",
      safe_next_step: "Opisz własny temat.",
      candidates: [],
      source_connectors: ["ahrefs"],
      evidence_ids: ["ev_ahrefs"]
    });
    vi.mocked(getContentNewPagePlanningProposal).mockResolvedValue(newPagePlanningWorkspace());
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(canonicalDocumentWorkspace());
  });

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

  it("prefills only an exact evidence-bound topic and preserves the manual brief path", async () => {
    vi.mocked(getContentNewPageTopicRecommendations).mockResolvedValue({
      response_type: "content_new_page_topic_recommendations",
      contract_version: "content_new_page_topic_recommendations_v1",
      status: "ready",
      title: "Tematy potwierdzone przez dane",
      reason: "Dane są zgodne.",
      safe_next_step: "Uzupełnij brief.",
      candidates: [{
        candidate_id: "content_new_page_topic_operat",
        candidate_digest: "a".repeat(64),
        title: "Operat wodnoprawny",
        topic: "operat wodnoprawny",
        rationale: "Ahrefs i GSC są zgodne.",
        source_connectors: ["ahrefs", "google_search_console"],
        evidence_ids: ["ev_ahrefs", "ev_gsc"]
      }],
      source_connectors: ["ahrefs", "google_search_console"],
      evidence_ids: ["ev_ahrefs", "ev_gsc"]
    });

    renderEntry({ newPageOpen: true, newPageId: null });

    fireEvent.click(await screen.findByRole("button", { name: "Użyj tego tematu" }));
    expect(screen.getByLabelText("Roboczy tytuł strony")).toHaveValue("Operat wodnoprawny");
    expect(screen.getByText("Dowody tematu: ev_ahrefs, ev_gsc")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Wpisz własny temat" }));
    expect(screen.getByRole("button", { name: "Użyj tego tematu" })).toBeInTheDocument();
  });

  it("explains an empty recommendation list with the API-owned data blocker", () => {
    const diagnostics = {
      marketer_decision: {
        status: "blocked",
        decision: "Nie podejmuj decyzji contentowej bez odczytu.",
        why_it_matters: "Brakuje GSC i inventory WordPress.",
        safe_next_action: "Uruchom odczyt GSC i WordPress.",
        source_connector_labels: ["Google Search Console", "WordPress ekologus.pl"],
        evidence_ids: ["ev_gsc", "ev_wp"]
      },
      freshness_assessment: {
        missing_connector_ids: ["google_search_console", "wordpress_ekologus"],
        stale_connector_ids: []
      },
      connectors: [
        { id: "google_search_console", label: "Google Search Console" },
        { id: "wordpress_ekologus", label: "WordPress ekologus.pl" }
      ]
    } as unknown as ContentDiagnosticsResponse;

    renderEntry({ entry: { ...entry, recommendations: [] }, diagnostics });

    expect(screen.getByTestId("content-workflow-data-blocker")).toHaveTextContent("Nie podejmuj decyzji contentowej bez odczytu.");
    expect(screen.getByText(/Uruchom odczyt GSC i WordPress/)).toBeInTheDocument();
    expect(screen.getByText(/ev_gsc, ev_wp/)).toBeInTheDocument();
    expect(screen.getByTestId("content-required-source-refresh")).toHaveTextContent("Nie zmienia treści ani nie publikuje w WordPressie.");
  });

  it("starts only an API-owned read for a source the freshness assessment requires", async () => {
    vi.mocked(refreshConnector).mockResolvedValue({
      id: "refresh_gsc_test",
      connector_id: "google_search_console",
      connector_label: "Google Search Console",
      mode: "vendor_read",
      status: "completed",
      status_label: "odczyt zakończony",
      started_at: "2026-07-28T00:00:00Z",
      completed_at: "2026-07-28T00:00:01Z",
      evidence_ids: [],
      evidence_summary_label: "",
      missing_credentials: [],
      checked_credentials: [],
      external_call_attempted: true,
      vendor_data_collected: true,
      metrics_persisted: true,
      metric_summary: {},
      covered_window: undefined,
      settlement_state: "unknown",
      quality_state: "unknown",
      summary: "Odczyt zakończony.",
      errors: [],
      redacted: true
    });
    const diagnostics = {
      marketer_decision: {
        status: "blocked",
        decision: "Brakuje odczytu.",
        why_it_matters: "Bez źródła brak rekomendacji.",
        safe_next_action: "Odczytaj GSC.",
        source_connector_labels: ["Google Search Console"],
        evidence_ids: []
      },
      freshness_assessment: { missing_connector_ids: ["google_search_console"], stale_connector_ids: [] },
      connectors: [{ id: "google_search_console", label: "Google Search Console" }]
    } as unknown as ContentDiagnosticsResponse;

    renderEntry({ entry: { ...entry, recommendations: [] }, diagnostics });
    fireEvent.click(screen.getByRole("button", { name: "Odczytaj Google Search Console" }));

    await waitFor(() => expect(refreshConnector).toHaveBeenCalledWith("google_search_console"));
    expect(screen.getByRole("status")).toHaveTextContent("Odczyt zakończony.");
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

    await screen.findByText("Wybierz wiedzę dla tekstu");
    expect(screen.queryByLabelText("Potwierdza")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Wiedza o usłudze"), { target: { value: "service_environment" } });
    fireEvent.click(screen.getByRole("button", { name: "Użyj tej wiedzy do tekstu" }));

    await waitFor(() => expect(createContentNewPageFoundation).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_brief_digest: "a".repeat(64),
      expected_overlap_digest: "b".repeat(64),
      service_card_id: "service_environment",
      confirmed_by: "wilku"
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

  it("prepares the first new-page version from one exact generated-plan action", async () => {
    const readyPlan = newPagePlanningWorkspace();
    readyPlan.proposal_status = {
      ...readyPlan.proposal_status!,
      status: "ready",
      proposal: {
        proposal_id: "content_planning_proposal_test",
        planning_digest: "b".repeat(64),
        planning_input_digest: "d".repeat(64),
        sections: [{ section_id: "section_intro", heading: "Wprowadzenie", purpose: "Wyjaśnij temat." }]
      } as never
    };
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
    vi.mocked(getContentNewPagePlanningProposal).mockResolvedValue(readyPlan);
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue({
      ...canonicalDocumentWorkspace(),
      status: "ready_for_document"
    });
    vi.mocked(createContentNewPageInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "content_work_item_new_page_test",
      proposal_id: "content_planning_proposal_test",
      run_id: "codex_content_initial_draft_test",
      blockers: [{ code: "generation_in_progress", label: "Trwa", reason: "Trwa", next_step: "Poczekaj." }],
      safe_next_step: "Dokument jest przygotowywany.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, event_methods: [], item_types: [], external_call_attempted: false }
    } as never);

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj pierwszą wersję" }));

    expect(screen.getByText("Nie zatwierdzasz tu planu. Nie publikuje to strony ani nie tworzy szkicu WordPressa.")).toBeInTheDocument();

    await waitFor(() => expect(createContentNewPageInitialDraft).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_proposal_id: "content_planning_proposal_test",
      expected_planning_digest: "b".repeat(64),
      expected_planning_input_digest: "d".repeat(64),
      requested_by: "wilku"
    }));
    expect(screen.queryByLabelText("Reviewer")).not.toBeInTheDocument();
  });

  it("creates the first immutable new-page revision only from the exact reviewed plan", async () => {
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
    vi.mocked(createContentNewPageInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "content_work_item_new_page_test",
      proposal_id: "content_planning_proposal_test",
      run_id: "codex_content_initial_draft_test",
      revision: null,
      runtime: { status: "not_started", thread_id: null, turn_id: null, event_methods: [], item_types: [], external_call_attempted: false },
      blockers: [],
      safe_next_step: "Dokument jest przygotowywany.",
      publish_ready: false
    });

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-initial-draft")).toBeInTheDocument();
    expect(screen.queryByLabelText("Zleca")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj pierwszą wersję" }));

    await waitFor(() => expect(createContentNewPageInitialDraft).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_proposal_id: "content_planning_proposal_test",
      expected_planning_digest: "b".repeat(64),
      expected_planning_input_digest: "d".repeat(64),
      requested_by: "wilku"
    }));
  });

  it("approves the exact new-page revision without a reviewer form or checklist", async () => {
    const workspace = reviewRequiredCanonicalDocumentWorkspace();
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(workspace);
    vi.mocked(reviewContentNewPageRevision).mockResolvedValue({ status: "reviewed" } as never);

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-revision-review")).toBeInTheDocument();
    expect(screen.queryByLabelText("Reviewer")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Zatwierdź tekst" }));

    await waitFor(() => expect(reviewContentNewPageRevision).toHaveBeenCalledWith("content_new_page_brief_test", "content_draft_revision_new_page_test", {
      expected_revision_digest: "e".repeat(64),
      reviewed_by: "wilku",
      decision: "approved",
      notes: "",
      checked_items: ["Tekst sprawdzony względem planu i przypisanych źródeł."],
      evidence_ids: ["ev_new_page_source"]
    }));
  });

  it("prepares a delivery ActionObject without asking for a duplicate requester", async () => {
    const workspace = {
      ...reviewRequiredCanonicalDocumentWorkspace(),
      status: "document_approved" as const,
      document_status: "approved" as const
    };
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(workspace);
    vi.mocked(getContentNewPageDeliveryReadiness).mockResolvedValue({
      response_type: "content_new_page_delivery_readiness",
      contract_version: "content_new_page_delivery_readiness_v1",
      status: "ready_for_action",
      work_item_id: "content_work_item_new_page_test",
      brief_id: "content_new_page_brief_test",
      brief_digest: "a".repeat(64),
      foundation_id: "content_new_page_foundation_test",
      service_card_id: "service_environment",
      service_card_digest: "c".repeat(64),
      revision_id: "content_draft_revision_new_page_test",
      revision_digest: "e".repeat(64),
      authoring_profile_digest: "f".repeat(64),
      allowed_content_types: ["page"],
      evidence_ids: ["ev_new_page_source"],
      blockers: [],
      safe_next_step: "Przygotuj ActionObject."
    });
    vi.mocked(createContentNewPageDeliveryAction).mockResolvedValue({ id: "act_new_page_draft" } as never);

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-delivery-ready")).toBeInTheDocument();
    expect(screen.queryByLabelText("Przygotowuje")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj ActionObject" }));

    await waitFor(() => expect(createContentNewPageDeliveryAction).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_revision_digest: "e".repeat(64),
      expected_authoring_profile_digest: "f".repeat(64),
      content_type: "page",
      requested_by: "wilku"
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
    contract_version: "content_new_page_canonical_document_v3",
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

function reviewRequiredCanonicalDocumentWorkspace(): ContentNewPageCanonicalDocumentWorkspace {
  return {
    ...canonicalDocumentWorkspace(),
    status: "document_review_required",
    document_status: "unreviewed",
    canonical_revision: {
      revision_id: "content_draft_revision_new_page_test",
      content_digest: "e".repeat(64),
      sections: [{ evidence_ids: ["ev_new_page_source"] }]
    } as never
  };
}

function foundationFixture() {
  return {
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
      proposed_ia_location: "Usługi → Dokumentacja środowiskowa",
      topic_evidence_ids: []
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
