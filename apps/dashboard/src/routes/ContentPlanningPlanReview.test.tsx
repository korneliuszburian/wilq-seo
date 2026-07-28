import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  getContentWorkItemPlanningProposal,
  saveContentWorkItemPlanningReview
} from "../lib/api";
import { ContentPlanningPlanReview } from "./ContentPlanningPlanReview";

vi.mock("../lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/api")>()),
  getContentWorkItemPlanningProposal: vi.fn(),
  saveContentWorkItemPlanningReview: vi.fn()
}));

describe("ContentPlanningPlanReview", () => {
  it("reviews the exact generated plan before opening full-document generation", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan());
    vi.mocked(saveContentWorkItemPlanningReview).mockResolvedValue({
      status: "recorded",
      decision: {},
      planning_workspace: {}
    } as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningPlanReview workItemId="content_work_item_bdo" />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Sprawdź wygenerowany plan" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Zatwierdź plan do tekstu" }));

    await waitFor(() => {
      expect(saveContentWorkItemPlanningReview).toHaveBeenCalledWith(
        expect.objectContaining({
          stage: "scope",
          expected_planning_digest: "a".repeat(64),
          service_card_id: "ekologus_service_bdo_reporting",
          checked_items: ["plan, struktura i źródła"]
        }),
        "content_work_item_bdo"
      );
    });
  });

  it("renders the typed stale-plan recovery instead of a generic API error", async () => {
    vi.mocked(getContentWorkItemPlanningProposal).mockResolvedValue(readyPlan());
    vi.mocked(saveContentWorkItemPlanningReview).mockResolvedValue({
      code: "stale_plan",
      current_proposal_id: "content_planning_proposal_newer",
      current_planning_digest: "c".repeat(64),
      safe_next_step: "Odśwież aktualny plan."
    } as never);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <ContentPlanningPlanReview workItemId="content_work_item_bdo" />
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByRole("button", { name: "Zatwierdź plan do tekstu" }));

    await waitFor(() => {
      expect(saveContentWorkItemPlanningReview).toHaveBeenCalledTimes(1);
    });
    expect(await screen.findByText("Odśwież aktualny plan.")).toBeInTheDocument();
  });
});

function readyPlan() {
  return {
    status: "ready",
    work_item_id: "content_work_item_bdo",
    service_card_id: "ekologus_service_bdo_reporting",
    planning_input_digest: "b".repeat(64),
    proposal: null,
    planning_workspace: {
      proposal: {
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
      },
      scope_decision: null,
      section_map_decision: null,
      scope_current: false,
      section_map_current: false
    },
    runtime: { status: "completed", thread_id: null, turn_id: null, external_call_attempted: false },
    blockers: [],
    safe_next_step: "Sprawdź wygenerowany plan.",
    publish_ready: false
  } as never;
}
