import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { getContentNewPageBriefWorkspace, type ContentNewPageBriefWorkspace, type ContentWorkflowEntryResponse } from "../lib/api";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return { ...actual, getContentNewPageBriefWorkspace: vi.fn() };
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
});

function savedBriefWorkspace(overlap: Partial<ContentNewPageBriefWorkspace["overlap_guard"]> = {}): ContentNewPageBriefWorkspace {
  return {
    response_type: "content_new_page_brief_workspace",
    contract_version: "content_new_page_brief_workspace_v1",
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
    review_status: "blocked",
    review_reason: "Brief nie jest jeszcze dokumentem do review.",
    next_action_label: "Przygotowanie dokumentu zostanie udostępnione w następnym etapie"
  };
}
