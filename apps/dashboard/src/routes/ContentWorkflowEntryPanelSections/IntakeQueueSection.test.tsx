import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { IntakeQueueSection } from "./IntakeQueueSection";

const READ_BACK = {
  schema_version: "wilq_content_intake_v1" as const,
  queue_id: "content_intake_c47b408cbdf7d42231f3a277",
  request_id: "11111111-1111-4111-8111-111111111111",
  input_digest: "c47b408cbdf7d42231f3a277e6294e1ea74266dc18718c4b8a14173ec248171b",
  actor_id: "local_operator",
  actor_trust_level: "local_unverified" as const,
  status: "queued" as const,
  ask: "Odśwież stronę o operacie wodnoprawnym",
  provenance: [
    {
      field: "ask",
      provenance: "evidence" as const,
      detail: "Prośba powiązana z bieżącym katalogiem.",
      evidence_ids: ["ev_catalog_current"]
    }
  ],
  candidate_work_item_ids: [],
  candidate_paths: [],
  candidate_public_urls: [],
  blockers: [],
  safe_next_step: "Wybierz stronę z katalogu WILQ, aby przygotować brief.",
  generation_allowed: false as const,
  created_at: "2026-09-26T22:17:47.362054Z"
};

function renderSection() {
  vi.spyOn(api, "getContentRequestWorkflow").mockResolvedValue({
    schema_version: "wilq_request_workflow_state_v1",
    queue_id: READ_BACK.queue_id,
    status: "in_progress",
    current_step: "intake_accepted",
    gates: [],
    lineage_event_ids: [],
    latest_idempotency_key: null,
    event_count: 0,
    evidence_ids: [],
    blocker_code: null,
    blocker_owner: null,
    safe_next_step: "Wskaż istniejący adres z katalogu WILQ.",
    generation_allowed: false,
    updated_at: "2026-09-26T22:20:00Z"
  });
  vi.spyOn(api, "getContentResearchRead").mockResolvedValue({
    schema_version: "wilq_content_research_read_v1",
    queue_id: READ_BACK.queue_id,
    work_item_id: null,
    status: "blocked",
    page_url: null,
    canonical_path: null,
    identity_id: null,
    facts: [],
    blocked_sources: [],
    blockers: [
      {
        code: "research_target_missing",
        owner: "WILQ content workflow",
        detail: "Brak wybranej strony."
      }
    ],
    claim_gates: [],
    research_packet_created: false,
    action_created: false,
    generation_allowed: false,
    safe_next_step: "Wskaż istniejącą stronę, aby odczytać dowody."
  });
  vi.spyOn(api, "getContentBriefProposal").mockResolvedValue({
    schema_version: "wilq_content_brief_proposal_v1",
    queue_id: READ_BACK.queue_id,
    status: "blocked",
    route: "new_page",
    target_work_item_id: null,
    target_path: null,
    target_public_url: null,
    fields: [
      {
        field: "zakres",
        value: "operat wodnoprawny",
        provenance: "user_input",
        detail: "Z prośby operatora.",
        evidence_ids: []
      }
    ],
    blockers: [
      {
        code: "brief_route_missing_source",
        owner: "Wilku",
        detail: "Brief nie ma jeszcze zatwierdzonego źródła."
      }
    ],
    workflow_step: "research_read",
    research_status: "blocked",
    planning_proposal_created: false,
    action_created: false,
    generation_allowed: false,
    safe_next_step: "Wskaż dokładnie jedną istniejącą stronę albo zgłoś nową."
  });
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <IntakeQueueSection />
    </QueryClientProvider>
  );
}

describe("intake queue section", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("reads the persisted queue item back instead of trusting the create response", async () => {
    const create = vi.spyOn(api, "createContentIntakeRequest").mockResolvedValue({
      ...READ_BACK,
      queue_id: "content_intake_created_side_only",
      status: "blocked",
      blockers: [
        {
          code: "intake_target_missing",
          owner: "WILQ content workflow",
          detail: "Brak pasującego elementu katalogu."
        }
      ],
      safe_next_step: "Wskaż istniejący adres z katalogu WILQ."
    });
    const readBack = vi.spyOn(api, "getContentIntakeRequest").mockResolvedValue(READ_BACK);
    renderSection();

    fireEvent.change(screen.getByLabelText("Co chcesz osiągnąć?"), {
      target: { value: "Odśwież stronę o operacie wodnoprawnym" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Przyjmij prośbę" }));

    await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
    const request = create.mock.calls[0][0];
    expect(request.ask).toBe("Odśwież stronę o operacie wodnoprawnym");
    expect(request.request_id).toMatch(/^[0-9a-f-]{36}$/);
    await waitFor(() =>
      expect(readBack).toHaveBeenCalledWith("content_intake_created_side_only")
    );

    expect(await screen.findByText("content_intake_c47b408cbdf7d42231f3a277")).toBeInTheDocument();
    expect(screen.queryByText("content_intake_created_side_only")).not.toBeInTheDocument();
    expect(screen.getByText("W kolejce")).toBeInTheDocument();
    expect(screen.queryByText("Zablokowane")).not.toBeInTheDocument();
    expect(
      screen.getByText("Wybierz stronę z katalogu WILQ, aby przygotować brief.")
    ).toBeInTheDocument();
    expect(screen.getByText(/ev_catalog_current/)).toBeInTheDocument();
    expect(await screen.findByText("Przebieg pracy")).toBeInTheDocument();
    expect(await screen.findByText("Brief do sprawdzenia")).toBeInTheDocument();
  });

  it("shows the typed blocker and owner without raw payload when the queue item is blocked", async () => {
    vi.spyOn(api, "createContentIntakeRequest").mockResolvedValue({
      ...READ_BACK,
      status: "blocked",
      blockers: [
        {
          code: "demand_evidence_not_fresh",
          owner: "WILQ demand evidence",
          detail: "Brak świeżych danych popytu."
        }
      ],
      safe_next_step: "Odśwież dane popytu."
    });
    vi.spyOn(api, "getContentIntakeRequest").mockResolvedValue({
      ...READ_BACK,
      status: "blocked",
      blockers: [
        {
          code: "demand_evidence_not_fresh",
          owner: "WILQ demand evidence",
          detail: "Brak świeżych danych popytu."
        }
      ],
      safe_next_step: "Odśwież dane popytu."
    });
    renderSection();

    fireEvent.change(screen.getByLabelText("Co chcesz osiągnąć?"), {
      target: { value: "Napisz o nowej usłudze środowiskowej" }
    });
    fireEvent.click(screen.getByRole("button", { name: "Przyjmij prośbę" }));

    expect(await screen.findByText("Zablokowane")).toBeInTheDocument();
    expect(screen.getByText("Brak świeżych danych popytu.")).toBeInTheDocument();
    expect(screen.getByText(/WILQ demand evidence/)).toBeInTheDocument();
    expect(screen.getByText("Odśwież dane popytu.")).toBeInTheDocument();
  });
});
