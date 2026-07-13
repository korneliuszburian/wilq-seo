import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Workflow, WorkflowRun } from "../lib/api";
import { WorkflowsSurface } from "./OperatingRouteSurfaces";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: ReactNode; to?: string }) => (
    <a href={to}>{children}</a>
  )
}));

const workflows: Workflow[] = [
  {
    id: "daily_command",
    label: "Plan dnia WILQ",
    description: "Dzienny przegląd decyzji i blokad.",
    steps: [],
    status: "ready",
    status_label: "gotowe",
    route: "/command-center",
    route_label: "Centrum pracy",
    skill_id: "wilq-daily-command",
    safe_next_step: "Otwórz kolejkę pracy.",
    source_connectors: ["google_search_console"],
    source_connector_labels: ["Google Search Console"],
    source_connector_summary_label: "Google Search Console",
    evidence_ids: ["ev_daily"],
    evidence_summary_label: "1 dowód",
    action_ids: ["act_daily"],
    action_summary_label: "1 akcja",
    blocked_claims: ["roas"],
    blocked_claim_labels: ["ROAS"],
    blocked_claim_summary_label: "1 zablokowane twierdzenie",
    metric_tiles: {},
    missing_contracts: ["conversion"],
    missing_contract_labels: ["konwersje"],
    missing_contract_summary_label: "1 brakujący kontrakt",
    missing_contract_detail_label: "konwersje",
    risk: "low",
    risk_label: "niskie ryzyko"
  }
];

const workflowRuns: WorkflowRun[] = [
  {
    id: "run_daily_command",
    workflow_id: "daily_command",
    status: "queued",
    status_label: "w kolejce",
    started_at: "2026-07-13T07:00:00Z",
    completed_at: null,
    input: { connector_ids: ["google_search_console"], parameters: {} },
    output: {
      evidence_ids: ["ev_daily"],
      action_ids: ["act_daily"],
      errors: [],
      evidence_summary_label: "1 dowód",
      action_summary_label: "1 akcja",
      error_summary_label: ""
    }
  }
];

describe("WorkflowsSurface", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders persisted workflow proof and keeps technical details expandable", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/workflows")) return Promise.resolve(Response.json(workflows));
      if (url.endsWith("/api/workflow-runs")) return Promise.resolve(Response.json(workflowRuns));
      return Promise.reject(new Error(`Unexpected workflow request: ${url}`));
    }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <WorkflowsSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "Procesy WILQ" })).toBeInTheDocument();
    expect(screen.getByText("Procesy decyzyjne")).toBeInTheDocument();
    expect(screen.getByText("Plan dnia WILQ")).toBeInTheDocument();
    expect(screen.getByText("gotowe")).toBeInTheDocument();
    expect(screen.getByText("Brakujące dane: 1 brakujący kontrakt")).toBeInTheDocument();
    expect(screen.getByText("Granice wniosków: 1 zablokowane twierdzenie")).toBeInTheDocument();
    expect(screen.queryByText("daily_command")).not.toBeInTheDocument();
    expect(screen.queryByText("run_daily_command")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż uruchomienia (1)" }));
    expect(await screen.findByText("w kolejce")).toBeInTheDocument();
    expect(screen.queryByText("run_daily_command")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż wyniki procesów" }));
    expect(screen.getByText("Dowody z procesów")).toBeInTheDocument();
    expect(screen.getByText("Akcje z procesów")).toBeInTheDocument();
  });
});
