import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createContentNewPageDeliveryAction, createContentNewPageFoundation, createContentNewPageInitialDraft, createContentNewPagePlanningProposal, getContentNewPageBriefWorkspace, getContentNewPageCanonicalDocument, getContentNewPageDeliveryReadiness, getContentNewPagePlanningProposal, getContentNewPageTopicRecommendations, getContentRevisionPublicDeployment, refreshConnector, reviewContentNewPageRevision, type ContentDiagnosticsResponse, type ContentInventoryCatalogResponse, type ContentNewPageBriefWorkspace, type ContentNewPageCanonicalDocumentWorkspace, type ContentNewPagePlanningProposalWorkspace, type ContentWorkflowEntryResponse } from "../lib/api";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, createContentNewPageDeliveryAction: vi.fn(), createContentNewPageFoundation: vi.fn(), createContentNewPageInitialDraft: vi.fn(), createContentNewPagePlanningProposal: vi.fn(), getContentNewPageBriefWorkspace: vi.fn(), getContentNewPageCanonicalDocument: vi.fn(), getContentNewPageDeliveryReadiness: vi.fn(), getContentNewPagePlanningProposal: vi.fn(), getContentNewPageTopicRecommendations: vi.fn(), getContentRevisionPublicDeployment: vi.fn(), refreshConnector: vi.fn(), reviewContentNewPageRevision: vi.fn() };
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
    decision_mode: "refresh",
    decision_label: "odśwież istniejącą treść",
    decision_action: "do_it_now",
    blockers: [],
    reason: "Strona wymaga sprawdzenia na podstawie danych GSC.",
    facts: [{ label: "Wyświetlenia GSC", value: "107", period_label: "od 2026-07-01 do 2026-07-31" }]
  }],
  search_query: null,
  search_results: [],
  browse_inventory_label: "Przeglądaj cały serwis"
};

const inventoryCatalogItem: ContentInventoryCatalogResponse["items"][number] = {
  catalog_id: "catalog_coverage_test",
  work_item_id: "content_work_item_coverage_test",
  url: "https://www.ekologus.pl/coverage-test/",
  path: "/coverage-test/",
  title: "Strona testowa",
  content_type: "page",
  content_summary: "Strona testowa",
  content_word_count: 120,
  section_count: 0,
  acf_section_count: 0,
  acf_field_names: [],
  acf_section_headings: [],
  material_status: "content_summary",
  source_connector: "wordpress_ekologus",
  evidence_id: "ev_coverage_test",
  collected_at: "2026-09-12T00:00:00Z",
  metrics_status: "missing",
  metrics_evidence_ids: [],
  metrics_query_count: 0,
  metrics_clicks: 0,
  metrics_impressions: 0
};

const blockedEvidenceReadiness: NonNullable<ContentInventoryCatalogResponse["journal_readiness"]>["rows"][number]["content_evidence_readiness"] = {
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
};

const blockedEvidenceReadinessSummary: NonNullable<ContentInventoryCatalogResponse["journal_readiness"]>["content_evidence_readiness"] = {
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
};

const homepageEvidenceReadiness: typeof blockedEvidenceReadiness = {
  ...blockedEvidenceReadiness,
  authoring_inventory_receipt: {
    status: "current",
    receipt_id: "content_authoring_inventory_home",
    receipt_digest: "a".repeat(64),
    evidence_id: "ev_wp_home",
    collected_at: "2026-09-13T10:00:00Z",
    freshness: "fresh"
  },
  evidence_acquisition: {
    recorded_status: "ready_for_researcher",
    current_status: "ready_for_researcher",
    run_id: "content_evidence_acquisition_home",
    run_digest: "b".repeat(64),
    evidence_ids: ["ev_home_observation"],
    subject_kind: "identity_binding",
    subject_id: "content_delivery_identity_home",
    freshness: "fresh",
    blockers: [],
    safe_next_step: "Przekaż exact observation do researchera."
  },
  research_proposal: {
    status: "ready_for_review",
    proposal_id: "content_research_proposal_91afbb4d56b5f6ac696b237b",
    proposal_digest: "c".repeat(64),
    acquisition_run_id: "content_evidence_acquisition_home",
    review_required: true,
    approved: false,
    blockers: [],
    safe_next_step: "Przekaż propozycję do human review."
  },
  identity: {
    status: "exact_current",
    binding_id: "content_delivery_identity_home",
    binding_digest: "d".repeat(64),
    blockers: [],
    safe_next_step: "Exact current identity is available."
  },
  service_card: {
    status: "review_required",
    card_id: "ekologus_service_homepage_overview",
    card_status: "source_backed_review_required",
    evidence_ids: ["ev_content_service_profile_source_facts"],
    source_connectors: ["public_site"],
    blockers: [{ code: "service_card_review_required", reason: "Exact Service Profile card wymaga review.", evidence_ids: ["ev_content_service_profile_source_facts"], safe_next_step: "Zatwierdź exact Service Profile card przez człowieka." }],
    safe_next_step: "Zatwierdź exact Service Profile card przez człowieka."
  },
  promotion: {
    status: "blocked",
    receipt_id: null,
    source_fact_id: null,
    blockers: [{ code: "service_card_review_required", reason: "Promotion czeka na zatwierdzenie card.", evidence_ids: ["ev_content_service_profile_source_facts"], safe_next_step: "Zatwierdź exact Service Profile card przez człowieka." }],
    safe_next_step: "Zatwierdź exact Service Profile card przez człowieka."
  },
  blockers: [{ code: "service_card_review_required", reason: "Exact Service Profile card wymaga review.", evidence_ids: ["ev_content_service_profile_source_facts"], safe_next_step: "Zatwierdź exact Service Profile card przez człowieka." }],
  safe_next_step: "Zatwierdź exact Service Profile card przez człowieka."
};

const bdoEvidenceReadiness: typeof blockedEvidenceReadiness = {
  ...blockedEvidenceReadiness,
  authoring_inventory_receipt: {
    status: "current",
    receipt_id: "content_authoring_inventory_bdo",
    receipt_digest: "e".repeat(64),
    evidence_id: "ev_wp_bdo",
    collected_at: "2026-09-13T10:00:00Z",
    freshness: "fresh"
  },
  evidence_acquisition: {
    recorded_status: "ready_for_researcher",
    current_status: "ready_for_researcher",
    run_id: "content_evidence_acquisition_bdo",
    run_digest: "f".repeat(64),
    evidence_ids: ["ev_bdo_observation"],
    subject_kind: "authoring_inventory_receipt",
    subject_id: "content_authoring_inventory_bdo",
    freshness: "fresh",
    blockers: [],
    safe_next_step: "Przekaż exact observation do researchera."
  },
  research_proposal: {
    status: "ready_for_review",
    proposal_id: "content_research_proposal_2813b551069e5bc8dfd46dad",
    proposal_digest: "1".repeat(64),
    acquisition_run_id: "content_evidence_acquisition_bdo",
    review_required: true,
    approved: false,
    blockers: [],
    safe_next_step: "Przekaż propozycję do human review."
  },
  identity: {
    status: "missing",
    binding_id: null,
    binding_digest: null,
    blockers: [],
    safe_next_step: "Zwiąż exact current identity binding."
  },
  service_card: {
    status: "approved_current",
    card_id: "ekologus_service_bdo_reporting",
    card_status: "approved_current",
    evidence_ids: ["ev_content_service_profile_source_facts"],
    source_connectors: ["public_site"],
    blockers: [],
    safe_next_step: "Exact Service Profile card is current."
  },
  promotion: {
    status: "blocked",
    receipt_id: null,
    source_fact_id: null,
    blockers: [{ code: "promotion_identity_required", reason: "Promotion wymaga exact identity.", evidence_ids: [], safe_next_step: "Zwiąż exact current identity binding." }],
    safe_next_step: "Zwiąż exact current identity binding."
  },
  blockers: [{ code: "identity_binding_missing", reason: "Exact current identity binding is missing.", evidence_ids: [], safe_next_step: "Zwiąż exact current identity binding." }],
  safe_next_step: "Zwiąż exact current identity binding."
};

const homepageCatalogItem: ContentInventoryCatalogResponse["items"][number] = {
  ...inventoryCatalogItem,
  catalog_id: "catalog_homepage",
  work_item_id: "content_work_item_homepage",
  url: "https://www.ekologus.pl/",
  path: "/",
  title: "Strona główna",
  evidence_id: "ev_wp_home"
};

const bdoCatalogItem: ContentInventoryCatalogResponse["items"][number] = {
  ...inventoryCatalogItem,
  catalog_id: "catalog_bdo",
  work_item_id: "content_work_item_bdo",
  url: "https://www.ekologus.pl/bdo-co-musi-wiedziec-przedsiebiorca/",
  path: "/bdo-co-musi-wiedziec-przedsiebiorca/",
  title: "BDO dla przedsiębiorcy",
  evidence_id: "ev_wp_bdo"
};

const exactEvidenceReadinessSummary = {
  ...blockedEvidenceReadinessSummary,
  total_count: 2,
  blocked_count: 2,
  authoring_receipt_current_count: 2,
  authoring_receipt_missing_count: 0,
  acquisition_ready_count: 2,
  acquisition_missing_count: 0,
  research_ready_count: 2,
  research_missing_count: 0,
  identity_exact_current_count: 1,
  identity_missing_count: 1,
  service_card_approved_current_count: 1,
  service_card_review_required_count: 1
};

function inventoryCatalog(
  coverage: ContentInventoryCatalogResponse["coverage"],
  journalReconciliation: ContentInventoryCatalogResponse["journal_reconciliation"] = null,
  journalReadiness: ContentInventoryCatalogResponse["journal_readiness"] = null,
  items: ContentInventoryCatalogResponse["items"] = [inventoryCatalogItem]
): ContentInventoryCatalogResponse {
  return {
    status: "ready",
    total_count: coverage.status === "complete" ? items.length : 139,
    ready_count: items.length,
    partial_count: 0,
    blocked_count: 0,
    items,
    source_connectors: ["wordpress_ekologus"],
    evidence_ids: ["ev_coverage_test"],
    coverage,
    journal_reconciliation: journalReconciliation,
    journal_readiness: journalReadiness
  };
}

function journalEvidenceRow(
  canonical_path: string,
  content_evidence_readiness: NonNullable<ContentInventoryCatalogResponse["journal_readiness"]>["rows"][number]["content_evidence_readiness"]
) {
  return {
    canonical_path,
    historical_as_of: "2026-08-28",
    content_kind: "service" as const,
    final_disposition: "keep" as const,
    historical_next_action: "review",
    operational_owner: "WILQ content workflow" as const,
    production_cohort: true,
    current_catalog_state: "exact_path_observed" as const,
    current_catalog_observation: null,
    content_evidence_readiness
  };
}

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
    expect(screen.getByText("Wyświetlenia GSC (od 2026-07-01 do 2026-07-31)")).toBeInTheDocument();
    expect(screen.getByText("Zrób teraz: odśwież istniejącą treść")).toBeInTheDocument();
    expect(screen.queryByText(/808 adresów/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /otwórz stronę/i }));
    expect(props.onSelectWorkItem).toHaveBeenCalledWith("content_work_item_bdo");
  });

  it("shows a blocked decision and the first blocker on the recommendation card", () => {
    renderEntry({
      entry: {
        ...entry,
        recommendations: [{
          ...entry.recommendations[0],
          decision_mode: "block",
          decision_label: "wstrzymaj pracę",
          decision_action: "wait_or_block",
          blockers: [{ code: "missing_evidence", label: "aktualnych danych GSC" }]
        }]
      }
    });

    expect(screen.getByText("Nie teraz: aktualnych danych GSC")).toBeInTheDocument();
    expect(screen.getByText("Brakuje: aktualnych danych GSC")).toBeInTheDocument();
  });

  it("keeps the catalog and new-page brief behind explicit choices", () => {
    const props = renderEntry();

    fireEvent.click(screen.getByRole("button", { name: /przeglądaj cały serwis/i }));
    expect(props.onBrowseInventory).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: /zacznij od briefu/i }));
    expect(props.onOpenNewPage).toHaveBeenCalledOnce();
  });

  it("states when the inventory browse range is incomplete and preserves the complete label", () => {
    const caveat = "Ostatni odczyt sitemap był częściowy albo niedostępny; nie traktuj inventory jako pełnego.";
    const journalRows = Array.from({ length: 214 }, (_, index) => ({
      canonical_path: index === 0 ? "/coverage-test" : `/historyczna-pozycja-${index}`,
      historical_as_of: "2026-08-28",
      content_kind: "editorial",
      final_disposition: "keep" as const,
      historical_next_action: "review",
      operational_owner: "WILQ content workflow" as const,
      production_cohort: true,
      current_catalog_state: index === 0 ? "not_observed" as const : index === 1 ? "ambiguous" as const : "exact_path_observed" as const,
      current_catalog_observation: null,
      content_evidence_readiness: blockedEvidenceReadiness
    }));

    renderEntry({
      browseInventory: true,
      inventory: inventoryCatalog(
        { status: "unknown", returned_count: 1, caveat },
        {
          status: "incomplete",
          journal_record_count: 214,
          matched_catalog_count: 127,
          missing_inventory_binding_count: 87,
          catalog_outside_journal_count: 12,
          matched_authoring_source_count: 175,
          missing_authoring_source_count: 39,
          missing_inventory_by_content_kind: { service: 44, taxonomy_or_system: 38 },
          caveat: "Część kanonicznych URL-i nie ma dokładnego typed inventory.",
          safe_next_step: "Zarejestruj exact inventory bindingi."
        },
        {
          status: "blocked",
          journal_record_count: 214,
          catalog_coverage_status: "unknown",
          content_evidence_readiness: blockedEvidenceReadinessSummary,
          rows: journalRows,
          caveat: "Historyczne decyzje nie są bieżącą authority.",
          safe_next_step: "Uzupełnij bieżący inventory."
        }
      )
    });

    expect(screen.getByTestId("content-workflow-inventory-coverage-warning")).toHaveTextContent(caveat);
    expect(screen.getByText("Zakres katalogu nie jest pełny")).toBeInTheDocument();
    expect(screen.queryByText("Przeglądaj cały serwis")).not.toBeInTheDocument();
    expect(screen.queryByText("Publiczne strony do odświeżenia")).not.toBeInTheDocument();
    expect(screen.getByText("Wyniki: 1 z 139 wykrytych adresów")).toBeInTheDocument();
    expect(screen.getByTestId("content-workflow-inventory-journal-reconciliation")).toHaveTextContent("127 z 214");
    expect(screen.getByTestId("content-workflow-inventory-journal-reconciliation")).toHaveTextContent("87 bez exact inventory binding");
    expect(screen.getByTestId("content-workflow-inventory-journal-reconciliation")).toHaveTextContent("175 URL-i ma bezpieczny odczyt authoring");
    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("214 URL-i");
    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("212 ma bieżącą exact obserwację");
    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("1 bez bieżącej exact obserwacji");
    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("1 niejednoznaczna");
    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("nie są bieżącą authority");
    expect(screen.getByText("Zablokowane")).toHaveAttribute("data-state", "blocked");
    const details = screen.getByText("Pokaż blocker i źródła").closest("details");
    expect(details).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("Pokaż blocker i źródła"));
    expect(details).toHaveAttribute("open");
    expect(screen.queryByText("content_work_item_coverage_test")).not.toBeInTheDocument();

    cleanup();
    renderEntry({
      browseInventory: true,
      inventory: inventoryCatalog({ status: "complete", returned_count: 1, caveat: "" })
    });

    expect(screen.getByText("Przeglądaj cały serwis")).toBeInTheDocument();
    expect(screen.getByText("Publiczne strony do odświeżenia")).toBeInTheDocument();
    expect(screen.queryByTestId("content-workflow-inventory-coverage-warning")).not.toBeInTheDocument();
    expect(screen.queryByTestId("content-workflow-inventory-journal-reconciliation")).not.toBeInTheDocument();
    expect(screen.getByText("Wyniki: 1 z 1 adresów")).toBeInTheDocument();
  });

  it("renders exact homepage and BDO blockers from the evidence projection", () => {
    const journalReadiness: NonNullable<ContentInventoryCatalogResponse["journal_readiness"]> = {
      status: "blocked",
      journal_record_count: 2,
      catalog_coverage_status: "partial",
      rows: [
        journalEvidenceRow("/", homepageEvidenceReadiness),
        journalEvidenceRow("/bdo-co-musi-wiedziec-przedsiebiorca", bdoEvidenceReadiness)
      ],
      content_evidence_readiness: exactEvidenceReadinessSummary,
      caveat: "Historyczne decyzje nie są bieżącą authority.",
      safe_next_step: "Usuń exact blocker przed kolejnym krokiem."
    };

    renderEntry({
      browseInventory: true,
      inventory: inventoryCatalog(
        { status: "unknown", returned_count: 2, caveat: "Katalog jest niepełny." },
        null,
        journalReadiness,
        [homepageCatalogItem, bdoCatalogItem]
      )
    });

    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("Gotowość dowodowa: 2 URL-i");
    expect(screen.getByTestId("content-workflow-inventory-journal-readiness")).toHaveTextContent("Blokady — identity: 1; karta: 1; promocja: 2");
    expect(screen.getByText("Exact Service Profile card wymaga review.")).toBeInTheDocument();
    expect(screen.getByText("Exact current identity binding is missing.")).toBeInTheDocument();
    expect(screen.getAllByText("Zablokowane")).toHaveLength(2);
  });

  it("does not use partial journal rows as full observation counts", () => {
    renderEntry({
      browseInventory: true,
      inventory: inventoryCatalog(
        { status: "unknown", returned_count: 1, caveat: "Katalog jest niepełny." },
        null,
        {
          status: "blocked",
          journal_record_count: 214,
          catalog_coverage_status: "unknown",
          rows: [{
            canonical_path: "/jedna-pozycja",
            historical_as_of: "2026-08-28",
            content_kind: "editorial",
            final_disposition: "keep",
            historical_next_action: "review",
            operational_owner: "WILQ content workflow",
            production_cohort: true,
            current_catalog_state: "not_observed",
            current_catalog_observation: null,
            content_evidence_readiness: blockedEvidenceReadiness
          }],
          content_evidence_readiness: blockedEvidenceReadinessSummary,
          caveat: "Brak pełnego zestawu journalu.",
          safe_next_step: "Przywróć kompletny odczyt."
        }
      )
    });

    const readiness = screen.getByTestId("content-workflow-inventory-journal-readiness");
    expect(readiness).toHaveTextContent("przekazał tylko 1 z 214 oczekiwanych rekordów");
    expect(readiness).toHaveTextContent("nie używaj liczników obserwacji do decyzji");
    expect(readiness).not.toHaveTextContent("1 bez bieżącej exact obserwacji");
  });

  it("prefills only an exact evidence-bound topic and preserves the manual brief path", async () => {
    const evidenceIds = Array.from({ length: 22 }, (_, index) => `ev_topic_${index}`);
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
        evidence_ids: evidenceIds
      }],
      source_connectors: ["ahrefs", "google_search_console"],
      evidence_ids: evidenceIds
    });

    renderEntry({ newPageOpen: true, newPageId: null });

    fireEvent.click(await screen.findByRole("button", { name: "Użyj tego tematu" }));
    expect(screen.getByLabelText("Roboczy tytuł strony")).toHaveValue("Operat wodnoprawny");
    expect(screen.getByText("Dowody tematu: 22 dowody źródłowe")).toBeInTheDocument();
    expect(screen.queryByText(/ev_topic_0/)).not.toBeInTheDocument();
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
    expect(screen.getByText("Dowody źródłowe są dostępne w szczegółach pracy.")).toBeInTheDocument();
    expect(screen.queryByText(/ev_gsc, ev_wp/)).not.toBeInTheDocument();
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
    expect(screen.getByText("Dowody sprawdzonego katalogu: 1 dowód źródłowy")).toBeInTheDocument();
    expect(screen.queryByText(/ev_wp_other/)).not.toBeInTheDocument();
  });

  it("uses one marketer action to bind the source of knowledge before preparing text", async () => {
    vi.mocked(getContentNewPageBriefWorkspace)
      .mockResolvedValueOnce(savedBriefWorkspace())
      .mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(createContentNewPageFoundation).mockResolvedValue({
      status: "created",
      foundation: null,
      reason: "Podstawa zapisana.",
      safe_next_step: "Przygotuj plan dokumentu w kolejnym etapie workflow."
    });
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
    vi.mocked(getContentNewPagePlanningProposal).mockResolvedValue(readyPlan);
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(canonicalDocumentWorkspace());

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    await screen.findByText("Na czym oprzeć tekst?");
    expect(screen.queryByLabelText("Potwierdza")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Źródło wiedzy"), { target: { value: "service_environment" } });
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst na tej podstawie" }));

    await waitFor(() => expect(createContentNewPageFoundation).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_brief_digest: "a".repeat(64),
      expected_overlap_digest: "b".repeat(64),
      service_card_id: "service_environment",
      confirmed_by: "wilku"
    }));
    await waitFor(() => expect(createContentNewPageInitialDraft).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_proposal_id: "content_planning_proposal_test",
      expected_planning_digest: "b".repeat(64),
      expected_planning_input_digest: "d".repeat(64),
      requested_by: "wilku"
    }));
  });

  it("starts exact new-page preparation from one marketer-facing text action", async () => {
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
    expect(screen.queryByText("Przygotuj pierwszą immutable rewizję.")).not.toBeInTheDocument();
    expect(screen.getByText(/po przygotowaniu tekst pojawi się tutaj w całości/i)).toBeInTheDocument();
    expect(getContentNewPageCanonicalDocument).toHaveBeenCalledWith("content_new_page_brief_test");
    expect(createContentNewPagePlanningProposal).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst" }));

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

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(createContentNewPageInitialDraft).toHaveBeenCalledWith("content_new_page_brief_test", {
      expected_proposal_id: "content_planning_proposal_test",
      expected_planning_digest: "b".repeat(64),
      expected_planning_input_digest: "d".repeat(64),
      requested_by: "wilku"
    }));
    expect(screen.queryByLabelText("Reviewer")).not.toBeInTheDocument();
  });

  it("approves the exact new-page revision without a reviewer form or checklist", async () => {
    const workspace = reviewRequiredCanonicalDocumentWorkspace();
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(workspace);
    vi.mocked(reviewContentNewPageRevision).mockResolvedValue({ status: "reviewed" } as never);

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-document-preview")).toBeInTheDocument();
    expect(screen.getByText("Tekst strony · wersja robocza")).toBeInTheDocument();
    expect(screen.queryByTestId("new-page-planning-ready")).not.toBeInTheDocument();
    expect(getContentNewPagePlanningProposal).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText("Materiały i wiedza użyte w tej wersji"));
    expect(screen.getByText("Obsługa środowiskowa i zgodność obowiązków")).toBeInTheDocument();
    expect(screen.getByText(/Zapisane materiały: fact_service_environment/)).toBeInTheDocument();
    expect(await screen.findByTestId("new-page-revision-review")).toBeInTheDocument();
    expect(screen.queryByLabelText("Reviewer")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Zatwierdź tekst" }));

    await waitFor(() => expect(reviewContentNewPageRevision).toHaveBeenCalledWith("content_new_page_brief_test", "content_draft_revision_new_page_test", {
      expected_revision_digest: "e".repeat(64),
      reviewed_by: "wilku",
      decision: "approved",
      notes: "",
      checked_items: ["Tekst sprawdzony względem briefu, wybranej wiedzy i przypisanych źródeł."],
      evidence_ids: ["ev_new_page_source"]
    }));
  });

  it("does not offer review of a new page whose full text cannot be rendered", async () => {
    const workspace = reviewRequiredCanonicalDocumentWorkspace();
    (workspace.canonical_revision as { page_assets?: unknown }).page_assets = undefined;
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(workspace);

    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-document-preview-blocker")).toBeInTheDocument();
    expect(screen.queryByTestId("new-page-revision-review")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Zatwierdź tekst" })).not.toBeInTheDocument();
  });

  it("shows delivery readiness for an approved text while keeping delivery actions out", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(approvedCanonicalDocumentWorkspace());
    vi.mocked(getContentNewPageDeliveryReadiness).mockResolvedValue({
      response_type: "content_new_page_delivery_readiness",
      contract_version: "content_new_page_delivery_readiness_v1",
      status: "blocked",
      work_item_id: "content_work_item_new_page_test",
      brief_id: "content_new_page_brief_test",
      brief_digest: "a".repeat(64),
      foundation_id: "content_new_page_foundation_test",
      service_card_id: "service_environment",
      service_card_digest: "c".repeat(64),
      revision_id: null,
      revision_digest: null,
      allowed_content_types: [],
      authoring_profile_digest: null,
      evidence_ids: [],
      blockers: ["authoring_profile_missing"],
      safe_next_step: "Uzupełnij profil autorski, aby przekazać tekst na dev."
    });
    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-document-preview")).toBeInTheDocument();
    expect(await screen.findByTestId("new-page-delivery-readiness")).toBeInTheDocument();
    expect(
      screen.getByText("Uzupełnij profil autorski, aby przekazać tekst na dev.")
    ).toBeInTheDocument();
    expect(getContentNewPageDeliveryReadiness).toHaveBeenCalledWith("content_new_page_brief_test");
    expect(screen.queryByText("Przygotowanie akcji dev")).not.toBeInTheDocument();
    expect(screen.queryByText("Potwierdzenie publicznego wdrożenia")).not.toBeInTheDocument();
    expect(createContentNewPageDeliveryAction).not.toHaveBeenCalled();
    expect(getContentRevisionPublicDeployment).not.toHaveBeenCalled();
  });

  it("shows the ready delivery step for an approved text without starting it", async () => {
    vi.mocked(getContentNewPageBriefWorkspace).mockResolvedValue(savedBriefWorkspace({}, { foundation: foundationFixture() }));
    vi.mocked(getContentNewPageCanonicalDocument).mockResolvedValue(approvedCanonicalDocumentWorkspace());
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
      allowed_content_types: ["page"],
      authoring_profile_digest: "f".repeat(64),
      evidence_ids: ["ev_new_page_source"],
      blockers: [],
      safe_next_step: "Przygotuj jeden szkic dev z tej dokładnej rewizji."
    });
    renderEntry({ newPageOpen: true, newPageId: "content_new_page_brief_test" });

    expect(await screen.findByTestId("new-page-delivery-readiness")).toBeInTheDocument();
    expect(
      screen.getByText("Przygotuj jeden szkic dev z tej dokładnej rewizji.")
    ).toBeInTheDocument();
    expect(createContentNewPageDeliveryAction).not.toHaveBeenCalled();
    expect(getContentRevisionPublicDeployment).not.toHaveBeenCalled();
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
    expect(screen.getByText("Dowody: 1 dowód źródłowy")).toBeInTheDocument();
    expect(screen.queryByText(/ev_wp_audit/)).not.toBeInTheDocument();
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
    document_lineage: {
      status: "not_recorded",
      source_material_ids: [],
      knowledge_cards: [],
      unresolved_knowledge_card_ids: [],
      reason: "Nie ma jeszcze zapisanej rewizji, więc WILQ nie może wskazać materiałów przypisanych do dokumentu."
    },
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
    assigned_source_material_ids: ["fact_service_environment"],
    assigned_knowledge_card_ids: ["ekologus_service_environmental_compliance"],
    document_lineage: {
      status: "available",
      source_material_ids: ["fact_service_environment"],
      knowledge_cards: [{
        id: "ekologus_service_environmental_compliance",
        title: "Obsługa środowiskowa i zgodność obowiązków",
        summary: "Zatwierdzona wiedza o usłudze."
      }],
      unresolved_knowledge_card_ids: [],
      reason: "To są materiały i karty wiedzy zapisane przy dokładnej rewizji dokumentu."
    },
    canonical_revision: {
      work_item_id: "content_work_item_new_page_test",
      revision_id: "content_draft_revision_new_page_test",
      content_digest: "e".repeat(64),
      title: "Audyt środowiskowy dla inwestycji",
      sections: [{
        section_id: "new_page_section_01",
        heading: "Jak przygotować dokumentację",
        body_markdown: "Treść nowej strony.",
        evidence_ids: ["ev_new_page_source"]
      }],
      faq: [],
      cta_blocks: [],
      internal_links: [],
      source_material_ids: ["fact_service_environment"],
      knowledge_card_ids: ["ekologus_service_environmental_compliance"],
      page_assets: {
        meta_title: "Audyt środowiskowy dla inwestycji | Ekologus",
        meta_description: "Pomoc przy dokumentacji środowiskowej inwestycji.",
        h1: "Audyt środowiskowy dla inwestycji",
        lead: "Dowiedz się, jak przygotować dokumentację."
      }
    } as never
  };
}

function approvedCanonicalDocumentWorkspace(): ContentNewPageCanonicalDocumentWorkspace {
  const workspace = reviewRequiredCanonicalDocumentWorkspace();
  const revision = workspace.canonical_revision!;
  return {
    ...workspace,
    status: "document_approved",
    document_status: "approved",
    revision_review: {
      decision_id: "content_draft_revision_review_new_page_test",
      decision_number: 1,
      work_item_id: workspace.work_item_id,
      revision_id: revision.revision_id,
      revision_digest: revision.content_digest,
      reviewed_by: "Wilku",
      decision: "approved",
      notes: "Zatwierdzam dokładną rewizję.",
      checked_items: ["Tekst sprawdzony względem briefu i źródeł."],
      evidence_ids: ["ev_new_page_source"],
      created_at: "2026-09-27T00:00:00Z"
    }
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
        regulatory_requirement_ids: [],
        regulatory_source_fact_ids: [],
        regulatory_requirement_coverage: [],
        regulatory_review_candidates: [],
        evidence_id_count: 1,
        knowledge_card_count: 1,
        measurement_metrics: [],
        gsc_query_rows: [],
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
        regulatory_requirement_ids: [],
        regulatory_source_fact_ids: [],
        regulatory_requirement_coverage: [],
        regulatory_review_candidates: [],
        evidence_id_count: 1,
        knowledge_card_count: 1,
        measurement_metrics: [],
        gsc_query_rows: [],
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
