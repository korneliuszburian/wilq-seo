import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemInitialDraft,
  getContentWorkItemPlanningProposal,
  postContentWorkItemInitialDraft,
  postContentWorkItemPlanningProposal
} from "../lib/api";
import { ContentTextPreparationPanel } from "./ContentTextPreparationPanel";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemInitialDraft: vi.fn(),
  getContentWorkItemPlanningProposal: vi.fn(),
  postContentWorkItemInitialDraft: vi.fn(),
  postContentWorkItemPlanningProposal: vi.fn()
}));

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><ContentTextPreparationPanel workItemId="work_item" /></QueryClientProvider>);
}

function readyToGenerate(status: "not_generated" | "failed" = "not_generated") {
  return {
    status,
    work_item_id: "work_item",
    service_card_id: "service_card",
    planning_input_digest: "a".repeat(64),
    proposal: null,
    blockers: [],
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
    safe_next_step: "Przygotuj strukturę.",
    publish_ready: false
  };
}

describe("ContentTextPreparationPanel", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(cleanup);

  it("starts one exact planning request from the ready state with one marketer-facing action", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyToGenerate() as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({ ...readyToGenerate(), status: "generating", safe_next_step: "Poczekaj na strukturę." } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(postContentWorkItemPlanningProposal).toHaveBeenCalledWith({
      service_card_id: "service_card",
      expected_planning_input_digest: "a".repeat(64),
      operator_hint: "",
      requested_by: "wilku"
    }, "work_item"));
    expect(screen.queryByText("Następny krok")).not.toBeInTheDocument();
    expect(screen.queryByText(/zatwierdź plan/i)).not.toBeInTheDocument();
  });

  it("continues one requested text flow from a generated structure to the exact first draft", async () => {
    vi.mocked(getContentWorkItemPlanningProposal)
      .mockResolvedValueOnce(readyToGenerate() as never)
      .mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({
      ...readyToGenerate(),
      status: "generating"
    } as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValueOnce({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith({
      expected_proposal_id: "proposal_1",
      expected_planning_digest: "c".repeat(64),
      expected_planning_input_digest: "a".repeat(64),
      requested_by: "wilku"
    }, "work_item"));
  });

  it("uses an exact ready proposal to start the first text without a plan-approval step", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValueOnce({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledWith({
      expected_proposal_id: "proposal_1",
      expected_planning_digest: "c".repeat(64),
      expected_planning_input_digest: "a".repeat(64),
      requested_by: "wilku"
    }, "work_item"));
    expect(screen.queryByText("Szkic struktury tekstu")).not.toBeInTheDocument();
  });

  it("does not leak an internal plan-approval instruction into the marketer recovery action", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyToGenerate(),
      status: "blocked",
      blockers: [{
        code: "service_card_not_approved",
        label: "Brakuje zatwierdzonego źródła",
        reason: "Nie można jeszcze oprzeć tekstu na wybranej wiedzy.",
        next_step: "Zatwierdź plan."
      }]
    } as never);
    renderPanel();

    const recovery = (await screen.findByText(/Co wymaga uwagi:/)).parentElement;
    expect(recovery).toHaveTextContent("Brakuje zatwierdzonego źródła");
    expect(recovery).toHaveTextContent("Wybierz zatwierdzone źródło wiedzy, na którym ma oprzeć się tekst.");
    expect(screen.queryByText("Zatwierdź plan.")).not.toBeInTheDocument();
  });

  it("lets the marketer retry the same exact proposal after draft preparation fails", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft)
      .mockRejectedValueOnce(new Error("draft failed"))
      .mockResolvedValueOnce({
        status: "generating",
        work_item_id: "work_item",
        proposal_id: "proposal_1",
        run_id: "run_1",
        blockers: [],
        safe_next_step: "Poczekaj.",
        publish_ready: false,
        runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
      } as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValue({
      status: "generating",
      work_item_id: "work_item",
      proposal_id: "proposal_1",
      run_id: "run_1",
      blockers: [],
      safe_next_step: "Poczekaj.",
      publish_ready: false,
      runtime: { status: "started", thread_id: null, turn_id: null, external_call_attempted: false }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Nie udało się przygotować tekstu.");
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(2));
  });
});

function readyPlan() {
  return {
    ...readyToGenerate(),
    status: "ready",
    proposal: {
      proposal_id: "proposal_1",
      planning_digest: "c".repeat(64)
    }
  };
}
