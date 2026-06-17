import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const connectors = [
  {
    id: "google_ads",
    label: "Google Ads",
    status: "missing_credentials",
    configured: false,
    missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    freshness: { state: "missing" },
    supported_actions: []
  }
];

const opportunities = [
  {
    id: "opp_1",
    type: "google_ads_waste",
    title: "Google Ads diagnostics blocked until credentials are configured",
    domain: "google_ads",
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_1"],
    metrics: [],
    human_diagnosis: "Connector state is missing.",
    recommended_action: "Configure connector.",
    risk: "low",
    action_ids: ["act_1"],
    is_fixture: true
  }
];

const actions = [
  {
    id: "act_1",
    title: "Configure Google Ads access pack",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "low",
    status: "needs_validation",
    evidence_ids: ["ev_1"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis: "Google Ads connector cannot produce real metrics.",
    recommended_reason: "Credential setup unlocks reads.",
    payload: { action_type: "configure_connector" },
    audit_events: []
  }
];

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/api/dashboard/command-center")) {
        return Promise.resolve(
          Response.json({
            strict_instruction: "No WILQ API evidence means no marketing recommendation.",
            connector_summary: { total: 1, configured: 0, missing_credentials: 1 },
            sections: { todays_moves: opportunities },
            active_actions: actions,
            connector_health: connectors,
            codex_operator_status: {}
          })
        );
      }
      if (url.endsWith("/api/connectors")) return Promise.resolve(Response.json(connectors));
      if (url.endsWith("/api/opportunities")) return Promise.resolve(Response.json(opportunities));
      if (url.endsWith("/api/actions")) return Promise.resolve(Response.json(actions));
      if (url.endsWith("/api/workflows")) {
        return Promise.resolve(Response.json([{ id: "daily_command", label: "Daily Command", description: "Runs." }]));
      }
      return Promise.resolve(Response.json({}));
    })
  );
}

describe("WILQ dashboard", () => {
  beforeEach(() => {
    mockFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("command center renders", async () => {
    window.history.pushState({}, "", "/command-center");
    render(<App />);
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Command Center" })).toBeInTheDocument()
    );
    expect(screen.getByText("Today's Moves")).toBeInTheDocument();
  });

  it("connector status renders", async () => {
    window.history.pushState({}, "", "/command-center");
    render(<App />);
    await waitFor(() => expect(screen.getByText("Google Ads")).toBeInTheDocument());
    expect(screen.getByText("GOOGLE_ADS_DEVELOPER_TOKEN")).toBeInTheDocument();
  });

  it("opportunities route renders", async () => {
    window.history.pushState({}, "", "/opportunities");
    render(<App />);
    await waitFor(() =>
      expect(screen.getByText("Google Ads diagnostics blocked until credentials are configured")).toBeInTheDocument()
    );
  });

  it("action detail route renders", async () => {
    window.history.pushState({}, "", "/actions/act_1");
    render(<App />);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Configure Google Ads access pack" })
      ).toBeInTheDocument()
    );
  });

  it("missing connector state renders", async () => {
    window.history.pushState({}, "", "/ads-doctor");
    render(<App />);
    await waitFor(() => expect(screen.getAllByText("Missing credentials").length).toBeGreaterThan(0));
  });
});
