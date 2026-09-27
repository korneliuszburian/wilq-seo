import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { IntakeJourneyReadout } from "./IntakeJourneyReadout";

const QUEUE_ID = "content_intake_c47b408cbdf7d42231f3a277";

const RESEARCH = {
  schema_version: "wilq_content_research_read_v1" as const,
  queue_id: QUEUE_ID,
  work_item_id: null,
  status: "blocked" as const,
  page_url: null,
  canonical_path: null,
  identity_id: null,
  facts: [],
  blocked_sources: [
    {
      source_fact_id: "sf_bdo",
      review_status: "pending",
      source_url: "https://example.test/bdo",
      evidence_ids: ["ev_blocked_source"],
      reason_code: "source_fact_review_required" as const,
      blocker_owner: "Wilku",
      safe_next_step: "Zatwierdź fakt źródłowy BDO."
    }
  ],
  blockers: [
    {
      code: "research_target_missing",
      owner: "WILQ content workflow",
      detail: "Brak wybranej strony."
    }
  ],
  claim_gates: [
    {
      claim: "demand" as const,
      allowed: false as const,
      code: "demand_evidence_not_fresh",
      owner: "WILQ demand evidence",
      detail: "Brak świeżych danych popytu."
    }
  ],
  research_packet_created: false as const,
  action_created: false as const,
  generation_allowed: false as const,
  safe_next_step: "Wskaż istniejącą stronę, aby odczytać dowody."
};

const WORKFLOW = {
  schema_version: "wilq_request_workflow_state_v1" as const,
  queue_id: QUEUE_ID,
  status: "in_progress" as const,
  current_step: "research_read" as const,
  gates: [
    {
      code: "human_keeps_direction",
      status: "pending" as const,
      owner: "Wilku",
      evidence_ids: ["ev_gate"],
      safe_next_step: "Zatwierdź kierunek KEEP."
    }
  ],
  lineage_event_ids: ["evt_1"],
  latest_idempotency_key: "idem_1",
  event_count: 1,
  evidence_ids: ["ev_workflow"],
  blocker_code: null,
  blocker_owner: null,
  safe_next_step: "Zatwierdź kierunek KEEP w bramce.",
  generation_allowed: false as const,
  updated_at: "2026-09-26T22:20:00Z"
};

function renderReadout() {
  vi.spyOn(api, "getContentBriefProposal").mockResolvedValue({
    schema_version: "wilq_content_brief_proposal_v1",
    queue_id: QUEUE_ID,
    status: "ready",
    route: "existing_page",
    target_work_item_id: "wi_exact",
    target_path: "/operat-wodnoprawny",
    target_public_url: "https://ekologus.test/operat-wodnoprawny",
    fields: [
      {
        field: "zakres",
        value: "Operat wodnoprawny",
        provenance: "evidence",
        detail: "Zatwierdzony fakt źródłowy.",
        evidence_ids: ["ev_fact_a"]
      }
    ],
    blockers: [],
    workflow_step: "brief_ready",
    research_status: "ready",
    planning_proposal_created: false,
    action_created: false,
    generation_allowed: false,
    safe_next_step: "Otwórz existing-page workflow z tym briefem."
  });
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <IntakeJourneyReadout queueId={QUEUE_ID} />
    </QueryClientProvider>
  );
}

describe("intake journey readout", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("reads workflow and research for the same queue ID from the API", async () => {
    const workflow = vi.spyOn(api, "getContentRequestWorkflow").mockResolvedValue(WORKFLOW);
    const research = vi.spyOn(api, "getContentResearchRead").mockResolvedValue(RESEARCH);
    renderReadout();

    await waitFor(() => expect(workflow).toHaveBeenCalledWith(QUEUE_ID));
    await waitFor(() => expect(research).toHaveBeenCalledWith(QUEUE_ID));
  });

  it("shows decision, evidence, blocker and next safe step without raw payload", async () => {
    vi.spyOn(api, "getContentRequestWorkflow").mockResolvedValue(WORKFLOW);
    vi.spyOn(api, "getContentResearchRead").mockResolvedValue(RESEARCH);
    renderReadout();

    expect(await screen.findByText("Przebieg pracy")).toBeInTheDocument();

    expect(screen.getByText("Odczyt dowodów")).toBeInTheDocument();
    expect(screen.getByText("W toku")).toBeInTheDocument();
    expect(screen.getByText("Zatwierdź kierunek KEEP w bramce.")).toBeInTheDocument();
    expect(screen.getByText(/human_keeps_direction/)).toBeInTheDocument();
    expect(screen.getByText(/Zatwierdź kierunek KEEP\./)).toBeInTheDocument();

    expect(screen.getByText("Dowody zablokowane")).toBeInTheDocument();
    expect(screen.getByText(/sf_bdo/)).toBeInTheDocument();
    expect(screen.getByText(/Zatwierdź fakt źródłowy BDO\./)).toBeInTheDocument();
    expect(screen.getByText(/demand_evidence_not_fresh/)).toBeInTheDocument();
    expect(screen.getByText("Brak wybranej strony.")).toBeInTheDocument();
    expect(screen.getByText("Wskaż istniejącą stronę, aby odczytać dowody.")).toBeInTheDocument();

    expect(screen.getByText(/ev_workflow/)).toBeInTheDocument();
    expect(screen.getByText(/ev_gate/)).toBeInTheDocument();
    expect(screen.getByText("Brief do sprawdzenia")).toBeInTheDocument();
  });
});
