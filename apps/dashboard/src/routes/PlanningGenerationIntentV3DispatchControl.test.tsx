import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ActionObject } from "../lib/api";
import * as api from "../lib/api";
import { PlanningGenerationIntentV3DispatchControl } from "./PlanningGenerationIntentV3DispatchControl";

function intentAction(status: "ready_to_apply" | "applied"): ActionObject {
  return {
    id: "act_content_planning_generation_intent_v3_exact",
    title: "Zatwierdź lokalny zamiar planowania z pakietu v3",
    domain: "content",
    connector: "wordpress_ekologus",
    connector_label: "",
    mode: "apply",
    mode_label: "",
    risk: "low",
    risk_label: "",
    status,
    status_label: "",
    evidence_ids: ["ev_packet"],
    evidence_summary_label: "",
    metrics: [],
    human_diagnosis: "Apply zapisuje wyłącznie lokalny receipt zamiaru.",
    recommended_reason: "Sprawdź dokładny pakiet v3.",
    validation_status: "not_validated",
    validation_status_label: "",
    payload: {
      action_type: "content_planning_generation_intent_v3",
      local_authority_only: true
    },
    audit_events: []
  } as unknown as ActionObject;
}

function renderControl(action: ActionObject) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <PlanningGenerationIntentV3DispatchControl action={action} />
    </QueryClientProvider>
  );
}

describe("planning generation intent v3 dispatch control", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("does not offer dispatch before the intent receipt is applied", () => {
    renderControl(intentAction("ready_to_apply"));
    expect(screen.getByText(/Najpierw zatwierdź lokalny zamiar/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("dispatches the applied intent and shows the accepted proposal status", async () => {
    const dispatch = vi.spyOn(api, "dispatchPlanningGenerationIntentV3").mockResolvedValue({
      response_type: "planning_generation_intent_v3_dispatch",
      status: "accepted",
      action_id: "act_content_planning_generation_intent_v3_exact",
      work_item_id: "wi_exact",
      intent_receipt_id: "planning_generation_intent_receipt_exact",
      planning_input_digest: "3".repeat(64),
      proposal_status: "generating",
      blocker: null,
      safe_next_step: "Odczytaj status planu.",
      generation_performed: false,
      external_write_attempted: false
    });
    renderControl(intentAction("applied"));
    fireEvent.click(screen.getByRole("button", { name: "Uruchom planowanie z zatwierdzonego zamiaru" }));
    await waitFor(() =>
      expect(dispatch).toHaveBeenCalledWith("act_content_planning_generation_intent_v3_exact")
    );
    expect(await screen.findByRole("status")).toHaveTextContent("generating");
    expect(screen.getByText(/planning_generation_intent_receipt_exact/)).toBeInTheDocument();
  });

  it("shows the typed dispatch blocker without claiming generation", async () => {
    vi.spyOn(api, "dispatchPlanningGenerationIntentV3").mockResolvedValue({
      response_type: "planning_generation_intent_v3_dispatch",
      status: "blocked",
      action_id: "act_content_planning_generation_intent_v3_exact",
      work_item_id: "wi_exact",
      intent_receipt_id: null,
      planning_input_digest: null,
      proposal_status: null,
      blocker: {
        code: "research_packet_v3_current_drift",
        owner: "WILQ content workflow",
        evidence_ids: ["ev_packet"],
        safe_next_step: "Odczytaj aktualny pakiet i przygotuj nowy zamiar."
      },
      safe_next_step: "Odczytaj aktualny pakiet i przygotuj nowy zamiar.",
      generation_performed: false,
      external_write_attempted: false
    });
    renderControl(intentAction("applied"));
    fireEvent.click(screen.getByRole("button", { name: "Uruchom planowanie z zatwierdzonego zamiaru" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Odczytaj aktualny pakiet i przygotuj nowy zamiar."
    );
    expect(screen.getByText(/WILQ content workflow/)).toBeInTheDocument();
  });
});
