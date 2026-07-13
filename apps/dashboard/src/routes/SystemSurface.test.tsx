import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GenericSurface } from "./GenericSurface";
import { settingsConnectors } from "./settingsSurface.fixture";

const workflows = [
  {
    id: "daily_check",
    label: "Daily check",
    description: "Dzienny przegląd źródeł i blokad.",
    status: "blocked" as const,
    status_label: "zablokowane",
    risk: "medium" as const,
    risk_label: "średnie ryzyko"
  }
];

const workflowRuns = [
  {
    id: "run_daily_check_1",
    workflow_id: "daily_check",
    status: "completed" as const,
    status_label: "zakończone",
    started_at: "2026-07-13T07:00:00Z",
    completed_at: "2026-07-13T07:00:02Z",
    input: { connector_ids: ["google_search_console"], parameters: {} },
    output: { evidence_ids: ["ev_daily_check_1"], action_ids: [], errors: [] }
  }
];

describe("SystemSurface", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders technical audit mode without exposing raw connector internals", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/connectors")) return Promise.resolve(Response.json(settingsConnectors));
      if (url.endsWith("/api/workflows")) return Promise.resolve(Response.json(workflows));
      if (url.endsWith("/api/workflow-runs")) return Promise.resolve(Response.json(workflowRuns));
      return Promise.reject(new Error(`Unexpected system request: ${url}`));
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    });

    render(
      <QueryClientProvider client={queryClient}>
        <GenericSurface routeName="/system" />
      </QueryClientProvider>
    );

    expect(await screen.findByRole("heading", { name: "System" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Przegląd audytowy: status procesów, uruchomienia Codex, historia operatora i reguły bezpieczeństwa."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("procesów")).toBeInTheDocument();
    expect(screen.getByText("ostatnie uruchomienia")).toBeInTheDocument();
    expect(screen.getByText("obszary techniczne w review")).toBeInTheDocument();
    expect(screen.getByText("blokady systemowe")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Procesy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Uruchomienia Codex" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bezpieczeństwo" })).toBeInTheDocument();
    expect(screen.getByText("Brak zapisu zmian bez audytu")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Eksperymentalne obszary" })).toBeInTheDocument();
    expect(screen.getByText("Posty społecznościowe")).toBeInTheDocument();
    expect(screen.getByText("Eksporty Google Sheets")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Szczegóły techniczne" })).toBeInTheDocument();
    expect(screen.queryByText(/GOOGLE_ADS_DEVELOPER_TOKEN/)).not.toBeInTheDocument();
    expect(screen.queryByText("google_ads")).not.toBeInTheDocument();
    expect(screen.queryByText("Evidence Registry")).not.toBeInTheDocument();
    expect(screen.queryByText("CONNECTOR_REFRESH_RUN")).not.toBeInTheDocument();
    expect(screen.queryByText(/"action_type"/)).not.toBeInTheDocument();
  });
});
