import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { getContentWorkItemPlanningProposal, postContentWorkItemPlanningProposal } from "../lib/api";
import { ContentPlanningGenerationPanel } from "./ContentPlanningGenerationPanel";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemPlanningProposal: vi.fn(),
  postContentWorkItemPlanningProposal: vi.fn()
}));

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><ContentPlanningGenerationPanel workItemId="work_item" /></QueryClientProvider>);
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

describe("ContentPlanningGenerationPanel", () => {
  it("starts one exact planning request from the ready pre-plan state", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyToGenerate() as never);
    vi.mocked(postContentWorkItemPlanningProposal).mockResolvedValueOnce({ ...readyToGenerate(), status: "generating", safe_next_step: "Poczekaj na strukturę." } as never);
    renderPanel();

    fireEvent.click(await screen.findByRole("button", { name: "Przygotuj strukturę" }));
    await waitFor(() => expect(postContentWorkItemPlanningProposal).toHaveBeenCalledWith({
      service_card_id: "service_card",
      expected_planning_input_digest: "a".repeat(64),
      operator_hint: "",
      requested_by: "wilku"
    }, "work_item"));
  });

  it("keeps retry available after a failed run without a proposal", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      ...readyToGenerate("failed"),
      blockers: [{ code: "runtime_failed", label: "Nie udało się przygotować struktury", reason: "Runtime nie zwrócił bezpiecznego wyniku.", next_step: "Spróbuj ponownie.", source_codes: [] }]
    } as never);
    renderPanel();

    expect(await screen.findByRole("button", { name: "Spróbuj ponownie" })).toBeInTheDocument();
    expect(screen.getByText(/Runtime nie zwrócił bezpiecznego wyniku/)).toBeInTheDocument();
  });

  it("leaves a generated proposal to the single structure-review surface", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValueOnce({
      ...readyToGenerate(),
      status: "ready",
      proposal: { proposal_id: "proposal_1" }
    } as never);
    const { container } = renderPanel();

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});
