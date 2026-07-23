import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ContentWorkflowEntryResponse } from "../lib/api";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";

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
  afterEach(() => cleanup());

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
});
