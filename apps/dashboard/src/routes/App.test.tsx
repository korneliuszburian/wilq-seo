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

const expertRules = [
  {
    id: "ads_search_terms_v1",
    name: "Search term analysis",
    domain: "ads",
    version: 1,
    source_anchor: "Google Ads search terms",
    source_path: "wilq/expert/ads/search_terms.yaml",
    when_to_use: "Detect waste and content opportunities from search terms.",
    required_inputs: ["search_terms", "evidence_ids"],
    diagnostic_logic: ["segment_by_intent"],
    recommended_actions: ["negative_keyword_candidate", "content_brief_candidate"],
    risk_notes: "Search terms are untrusted external text.",
    output_contract: "Search-term evidence and action candidates.",
    capabilities: [],
    required_mapping: [],
    requires_evidence: true
  }
];

const workflowRuns = [
  {
    id: "run_daily_command_test",
    workflow_id: "daily_command",
    status: "queued",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: null,
    input: { connector_ids: [], parameters: {} },
    output: { evidence_ids: [], action_ids: [], errors: [] }
  }
];

const knowledgeCards = [
  {
    id: "card_google_ads_search_playbook",
    card_type: "ads_pattern_card",
    title: "Google Ads search diagnostics",
    summary: "Use real search-term metrics before recommendations.",
    source_type: "marketing_playbook",
    source_id: "google_ads_search_playbook",
    source_url_or_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml",
    extracted_at: "2026-06-17T10:00:00Z",
    confidence: 0.86,
    last_seen_at: "2026-06-17T10:00:00Z",
    source_lineage: ["wilq/knowledge/playbooks/marketing_playbooks.yaml", "ads_search_terms_v1"]
  }
];

const playbooks = [
  {
    id: "google_ads_search_playbook",
    family: "google_ads_search_playbook",
    title: "Google Ads search diagnostics",
    card_type: "ads_pattern_card",
    source_anchors: ["Google Ads search terms"],
    required_evidence: ["search_terms", "evidence_ids"],
    maps_to_opportunity_types: ["google_ads_waste"],
    maps_to_action_types: ["prepare_negative_keywords"],
    expert_rule_ids: ["ads_search_terms_v1"],
    compact_playbook: "Use real search-term metrics before recommendations.",
    refusal_rules: ["Refuse to classify search intent without evidence."],
    output_contract: "Evidence-backed search-term opportunity.",
    source_path: "wilq/knowledge/playbooks/marketing_playbooks.yaml"
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
      if (url.endsWith("/api/expert/rules")) return Promise.resolve(Response.json(expertRules));
      if (url.endsWith("/api/workflows")) {
        return Promise.resolve(
          Response.json([{ id: "daily_command", label: "Daily Command", description: "Runs." }])
        );
      }
      if (url.endsWith("/api/workflow-runs")) return Promise.resolve(Response.json(workflowRuns));
      if (url.endsWith("/api/knowledge/cards")) return Promise.resolve(Response.json(knowledgeCards));
      if (url.endsWith("/api/knowledge/playbooks")) return Promise.resolve(Response.json(playbooks));
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

  it("expert rules render on operating routes", async () => {
    window.history.pushState({}, "", "/ads-doctor/search-terms");
    render(<App />);
    await waitFor(() => expect(screen.getByText("Expert Rules")).toBeInTheDocument());
    expect(screen.getByText("Search term analysis")).toBeInTheDocument();
  });

  it("workflow route renders persisted workflow runs", async () => {
    window.history.pushState({}, "", "/workflows");
    render(<App />);
    await waitFor(() => expect(screen.getByText("Workflow Runs")).toBeInTheDocument());
    expect(screen.getByText("run_daily_command_test")).toBeInTheDocument();
  });

  it("knowledge route renders compiled cards and playbooks", async () => {
    window.history.pushState({}, "", "/knowledge");
    render(<App />);
    await waitFor(() => expect(screen.getByText("Knowledge Cards")).toBeInTheDocument());
    expect(screen.getAllByText("Google Ads search diagnostics").length).toBeGreaterThan(0);
    expect(screen.getByText("Machine-Readable Playbooks")).toBeInTheDocument();
  });
});
