import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../lib/api";
import { PlanningGenerationIntentV3Entry } from "./PlanningGenerationIntentV3Entry";

function renderEntry() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <PlanningGenerationIntentV3Entry
        workItemId="wi_exact"
        packetId="content_research_packet_v3_aaaaaaaaaaaaaaaaaaaaaaaa"
        packetDigest={"e".repeat(64)}
      />
    </QueryClientProvider>
  );
}

describe("planning generation intent v3 entry", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("prepares the intent for the exact packet and links its ActionObject", async () => {
    const prepare = vi.spyOn(api, "preparePlanningGenerationIntentV3Action").mockResolvedValue({
      response_type: "planning_generation_intent_v3",
      status: "preview_ready",
      action_id: "act_content_planning_generation_intent_v3_exact",
      action: {} as never,
      snapshot: {} as never,
      generation_performed: false,
      model_enqueued: false,
      external_write_attempted: false
    });
    renderEntry();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj zamiar planowania" }));
    await waitFor(() =>
      expect(prepare).toHaveBeenCalledWith(
        "wi_exact",
        "content_research_packet_v3_aaaaaaaaaaaaaaaaaaaaaaaa",
        "e".repeat(64)
      )
    );
    expect(await screen.findByRole("link", { name: "Otwórz zamiar planowania i decyzję" }))
      .toHaveAttribute("href", "/actions/act_content_planning_generation_intent_v3_exact");
  });

  it("shows the typed blocker and owner when the intent is blocked", async () => {
    vi.spyOn(api, "preparePlanningGenerationIntentV3Action").mockResolvedValue({
      response_type: "planning_generation_intent_v3",
      status: "blocked",
      work_item_id: "wi_exact",
      blocker_code: "research_packet_v3_approval_missing",
      blocker_owner: "WILQ content workflow",
      evidence_ids: ["ev_packet"],
      safe_next_step: "Zatwierdź dokładny pakiet v3.",
      generation_performed: false,
      model_enqueued: false,
      external_write_attempted: false
    });
    renderEntry();
    fireEvent.click(screen.getByRole("button", { name: "Przygotuj zamiar planowania" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Zatwierdź dokładny pakiet v3. Odpowiedzialny: WILQ content workflow."
    );
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
