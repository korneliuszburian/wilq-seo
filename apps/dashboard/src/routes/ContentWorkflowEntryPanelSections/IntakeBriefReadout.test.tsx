import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as api from "../../lib/api";
import { IntakeBriefReadout } from "./IntakeBriefReadout";

const QUEUE_ID = "content_intake_c47b408cbdf7d42231f3a277";

const READY_BRIEF = {
  schema_version: "wilq_content_brief_proposal_v1" as const,
  queue_id: QUEUE_ID,
  status: "ready" as const,
  route: "existing_page" as const,
  target_work_item_id: "wi_operat",
  target_path: "/operat-wodnoprawny",
  target_public_url: "https://ekologus.test/operat-wodnoprawny",
  fields: [
    {
      field: "zakres",
      value: "Operat wodnoprawny",
      provenance: "evidence" as const,
      detail: "Zatwierdzony fakt źródłowy.",
      evidence_ids: ["ev_fact_a"]
    }
  ],
  blockers: [],
  workflow_step: "brief_ready",
  research_status: "ready",
  planning_proposal_created: false as const,
  action_created: false as const,
  generation_allowed: false as const,
  safe_next_step: "Otwórz existing-page workflow z tym briefem."
};

function renderReadout() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <IntakeBriefReadout queueId={QUEUE_ID} />
    </QueryClientProvider>
  );
}

describe("intake brief readout", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("reads the reviewable brief for the same queue ID from the API", async () => {
    const brief = vi.spyOn(api, "getContentBriefProposal").mockResolvedValue(READY_BRIEF);
    renderReadout();
    await waitFor(() => expect(brief).toHaveBeenCalledWith(QUEUE_ID));
  });

  it("shows route, per-field provenance, target and next safe step", async () => {
    vi.spyOn(api, "getContentBriefProposal").mockResolvedValue(READY_BRIEF);
    renderReadout();

    expect(await screen.findByText("Brief do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("Gotowy do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("Istniejąca strona")).toBeInTheDocument();
    expect(screen.getByText("/operat-wodnoprawny")).toBeInTheDocument();
    expect(screen.getByText("https://ekologus.test/operat-wodnoprawny")).toBeInTheDocument();
    expect(screen.getByText(/zakres/)).toBeInTheDocument();
    expect(screen.getByText(/Operat wodnoprawny/)).toBeInTheDocument();
    expect(screen.getByText("Zatwierdzony fakt źródłowy.")).toBeInTheDocument();
    expect(screen.getByText(/z dowodów/)).toBeInTheDocument();
    expect(screen.getByText(/ev_fact_a/)).toBeInTheDocument();
    expect(screen.getByText("Otwórz existing-page workflow z tym briefem.")).toBeInTheDocument();
    expect(screen.getByText(/dowody gotowe/)).toBeInTheDocument();
  });

  it("shows the typed blocker and route when the brief is blocked", async () => {
    vi.spyOn(api, "getContentBriefProposal").mockResolvedValue({
      ...READY_BRIEF,
      status: "blocked",
      route: "new_page",
      target_work_item_id: null,
      target_path: null,
      target_public_url: null,
      blockers: [
        {
          code: "new_topic_discovery_source_unavailable",
          owner: "Wilku",
          detail: "Brak zatwierdzonego źródła discovery dla nowego tematu."
        }
      ],
      safe_next_step: "Zdecyduj źródło discovery albo wskaż istniejącą stronę."
    });
    renderReadout();

    expect(await screen.findByText("Zablokowany")).toBeInTheDocument();
    expect(screen.getByText("Nowa strona")).toBeInTheDocument();
    expect(
      screen.getByText("Brak zatwierdzonego źródła discovery dla nowego tematu.")
    ).toBeInTheDocument();
    expect(screen.getByText(/Wilku/)).toBeInTheDocument();
    expect(
      screen.getByText("Zdecyduj źródło discovery albo wskaż istniejącą stronę.")
    ).toBeInTheDocument();
  });
});
