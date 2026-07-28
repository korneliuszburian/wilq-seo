import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemInitialDraft,
  getContentWorkItemPlanningProposal,
  postContentWorkItemInitialDraft
} from "../lib/api";
import { ContentPlanningDraftStart } from "./ContentPlanningDraftStart";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemInitialDraft: vi.fn(),
  getContentWorkItemPlanningProposal: vi.fn(),
  postContentWorkItemInitialDraft: vi.fn()
}));

describe("ContentPlanningDraftStart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("prepares the full text from one exact generated-plan action", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan());
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "content_work_item_bdo",
      proposal_id: "proposal_bdo",
      run_id: "codex_run_bdo",
      blockers: [{ code: "generation_in_progress", label: "Trwa", reason: "Trwa", next_step: "Poczekaj." }],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "content_work_item_bdo",
      proposal_id: "proposal_bdo",
      run_id: "codex_run_bdo",
      blockers: [{ code: "generation_in_progress", label: "Trwa", reason: "Trwa", next_step: "Poczekaj." }],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningDraftStart workItemId="content_work_item_bdo" />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Szkic struktury tekstu" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj pełny tekst" }));

    await waitFor(() => {
      expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith(
        {
          expected_proposal_id: "proposal_bdo",
          expected_planning_digest: "a".repeat(64),
          expected_planning_input_digest: "b".repeat(64),
          requested_by: "wilku"
        },
        "content_work_item_bdo"
      );
    });
    expect(screen.getByText("Pełny tekst jest przygotowywany. Ten widok odświeży się po zakończeniu.")).toBeInTheDocument();
  });

  it("starts the full text without a separate plan decision", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan());
    vi.mocked(postContentWorkItemInitialDraft).mockRejectedValue(new Error("stale plan"));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningDraftStart workItemId="content_work_item_bdo" />
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj pełny tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(1));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nie udało się uruchomić tekstu.");
  });
});

function readyPlan() {
  const proposal = {
    work_item_id: "content_work_item_bdo",
    proposal_id: "proposal_bdo",
    planning_digest: "a".repeat(64),
    service_card_id: "ekologus_service_bdo_reporting",
    service_selection_confirmed: true,
    final_canonical_url: "https://www.ekologus.pl/bdo/",
    search_intent: "informacyjna",
    target_reader: "przedsiębiorca",
    cta_direction: "Skonsultuj obowiązki.",
    buyer_problem: "Nie wie, jak zacząć.",
    buyer_trigger: "Nowy obowiązek.",
    internal_link_directions: [],
    evidence_ids: ["evidence_bdo"],
    source_material_ids: [],
    knowledge_card_ids: [],
    source_connectors: ["wordpress_ekologus"],
    sections: [],
    generation_status: "codex_generated",
    search_demand: {
      gsc_query_rows: [],
      ads_term_rows: [],
      optional_ads_status: "not_available",
      safe_next_step: ""
    }
  };
  return {
    status: "ready",
    work_item_id: "content_work_item_bdo",
    service_card_id: "ekologus_service_bdo_reporting",
    planning_input_digest: "b".repeat(64),
    proposal,
    planning_workspace: null,
    runtime: { status: "completed", thread_id: null, turn_id: null, external_call_attempted: false },
    blockers: [],
    safe_next_step: "Sprawdź wygenerowany plan.",
    publish_ready: false
  } as never;
}
