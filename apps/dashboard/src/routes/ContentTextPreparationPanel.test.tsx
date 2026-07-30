import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
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

function renderPanel(onSelectedWorkspaceRead?: () => Promise<unknown>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    client,
    ...render(<QueryClientProvider client={client}>
      {onSelectedWorkspaceRead ? <SelectedWorkspaceObserver read={onSelectedWorkspaceRead} /> : null}
      <ContentTextPreparationPanel workItemId="work_item" />
    </QueryClientProvider>)
  };
}

function SelectedWorkspaceObserver({ read }: { read: () => Promise<unknown> }) {
  useQuery({
    queryKey: ["content-workflow", "work-item", "work_item", "selected-workspace"],
    queryFn: read,
    staleTime: Infinity
  });
  return null;
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

  it("shows only exact planning evidence and GSC queries used by the ready plan", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue({
      ...readyPlan(),
      input_summary: {
        ...readyToGenerate().input_summary,
        source_material_ids: ["material_1", "material_2"],
        knowledge_card_count: 3,
        evidence_id_count: 4,
        source_assessments: [
          { source: "wordpress", status: "used", reason: "Dokładny materiał.", evidence_ids: [] },
          { source: "gsc", status: "used", reason: "Dokładne zapytania.", evidence_ids: [] },
          { source: "ahrefs", status: "missing", reason: "Brak powiązania.", evidence_ids: [] }
        ]
      },
      proposal: {
        ...readyPlan().proposal,
        search_demand: {
          gsc_query_rows: [
            { term: "bdo dla firm", period: "2026-07", impressions: 181, clicks: 4 },
            { term: "bdo dla firm", period: "2026-06", impressions: 150, clicks: 3 },
            ...Array.from({ length: 5 }, (_, index) => ({ term: `zapytanie ${index}`, period: "2026-07", impressions: index, clicks: null }))
          ]
        }
      }
    } as never);
    renderPanel();

    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));

    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Materiały źródłowe");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Google Search Console");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("bdo dla firm · okres: 2026-07 · 181 wyświetleń · 4 kliknięć");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("bdo dla firm · okres: 2026-06 · 150 wyświetleń · 3 kliknięć");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Pokazano 6 z 7 exact zapytań GSC.");
    expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("Ahrefs");
  });

  it("replaces a POST planning state with fresher exact query evidence", async () => {
    const inputA = { ...readyToGenerate().input_summary, source_material_ids: ["material_a"], evidence_id_count: 1 };
    const inputB = { ...readyToGenerate().input_summary, source_material_ids: ["material_b", "material_c"], evidence_id_count: 2 };
    vi.mocked(getContentWorkItemPlanningProposal)
      .mockResolvedValueOnce({ ...readyToGenerate(), input_summary: inputA } as never)
      .mockResolvedValue({ ...readyToGenerate(), status: "blocked", input_summary: inputB, blockers: [{ code: "stale_input", label: "Nowe dane", reason: "B", next_step: "Odśwież." }] } as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({ ...readyToGenerate(), status: "generating", input_summary: inputA } as never);
    const { client } = renderPanel();
    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await client.refetchQueries({ queryKey: ["content-workflow", "work-item", "work_item", "planning-proposal"] });
    fireEvent.click(await screen.findByText("Na jakich danych oprze się tekst"));
    await waitFor(() => expect(screen.getByTestId("content-planning-evidence")).toHaveTextContent("2"));
    expect(screen.getByTestId("content-planning-evidence")).not.toHaveTextContent("material_a");
    expect(screen.queryByText("Przygotowuję pierwszy tekst")).not.toBeInTheDocument();
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

  it("refreshes the exact workspace when asynchronous draft preparation finishes", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft).mockResolvedValueOnce(initialDraft("generating") as never);
    vi.mocked(getContentWorkItemInitialDraft).mockResolvedValueOnce(initialDraft("created") as never);
    const selectedWorkspaceRead = vi.fn().mockResolvedValue({ canonical_document: { status: "created" } });
    const { client } = renderPanel(selectedWorkspaceRead);
    const invalidateQueries = vi.spyOn(client, "invalidateQueries");

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: ["content-workflow", "work-item", "work_item", "selected-workspace"]
    }));
    await waitFor(() => expect(selectedWorkspaceRead).toHaveBeenCalledTimes(3));
  });

  it("polls a retried exact draft through its terminal workspace refresh", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft)
      .mockResolvedValueOnce(initialDraft("generating") as never)
      .mockResolvedValueOnce(initialDraft("generating") as never);
    vi.mocked(getContentWorkItemInitialDraft)
      .mockResolvedValueOnce(initialDraft("failed") as never)
      .mockResolvedValueOnce(initialDraft("generating") as never)
      .mockResolvedValueOnce(initialDraft("created") as never);
    const selectedWorkspaceRead = vi.fn().mockResolvedValue({ canonical_document: { status: "created" } });
    const { client } = renderPanel(selectedWorkspaceRead);

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Przygotuj tekst" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj tekst" }));

    await waitFor(() => expect(postContentWorkItemInitialDraft).toHaveBeenCalledTimes(2));
    await client.refetchQueries({ queryKey: ["content-workflow", "work-item", "work_item", "initial-draft"] });
    await client.refetchQueries({ queryKey: ["content-workflow", "work-item", "work_item", "initial-draft"] });
    await waitFor(() => expect(getContentWorkItemInitialDraft).toHaveBeenCalledTimes(3));
    await waitFor(() => expect(selectedWorkspaceRead).toHaveBeenCalledTimes(4));
  });

  it("releases the exact draft guard when POST returns a typed terminal failure", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan() as never);
    vi.mocked(postContentWorkItemInitialDraft)
      .mockResolvedValueOnce(initialDraft("failed") as never)
      .mockResolvedValueOnce(initialDraft("generating") as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj tekst" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Przygotuj tekst" })).toBeEnabled());
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

function initialDraft(status: "generating" | "created" | "failed") {
  return {
    status,
    work_item_id: "work_item",
    proposal_id: "proposal_1",
    run_id: "run_1",
    blockers: status === "failed" ? [{
      code: "runtime_failed",
      label: "Nie udało się przygotować tekstu",
      reason: "Worker zakończył się błędem.",
      next_step: "Spróbuj ponownie."
    }] : [],
    safe_next_step: status === "created" ? "Otwórz tekst." : "Poczekaj.",
    publish_ready: false,
    runtime: { status: status === "failed" ? "failed" : "started", thread_id: null, turn_id: null, external_call_attempted: false }
  };
}
