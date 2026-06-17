import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, createWilqQueryClient, createWilqRouter } from "./App";

const connectors = [
  {
    id: "google_ads",
    label: "Google Ads",
    status: "missing_credentials",
    configured: false,
    missing_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    available_credential_sources: [],
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
    expert_rule_ids: ["ads_search_terms_v1"],
    playbook_ids: ["google_ads_search_playbook"],
    is_fixture: true
  }
];

const actions = [
  {
    id: "act_1",
    title: "Odnow Google Ads OAuth refresh token",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "low",
    status: "needs_validation",
    evidence_ids: ["ev_1"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis: "Google Ads refresh token returns oauth_error=invalid_grant.",
    recommended_reason: "OAuth repair unlocks reads.",
    payload: { action_type: "repair_google_ads_oauth" },
    audit_events: []
  }
];

const evidence = [
  {
    id: "ev_connector_google_ads_status",
    source_connector: "google_ads",
    source_type: "connector_status",
    source_id: "google_ads",
    collected_at: "2026-06-17T10:00:00Z",
    freshness: { state: "missing" },
    summary: "Connector google_ads is missing credential names.",
    raw_ref: null
  }
];

const connectorRefreshRuns = [
  {
    id: "refresh_google_ads_test",
    connector_id: "google_ads",
    mode: "status_probe",
    status: "completed",
    started_at: "2026-06-17T10:00:00Z",
    completed_at: "2026-06-17T10:00:01Z",
    evidence_ids: ["ev_connector_google_ads_status", "ev_refresh_refresh_google_ads_test"],
    missing_credentials: [],
    checked_credentials: ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    external_call_attempted: false,
    vendor_data_collected: false,
    metric_summary: {},
    summary: "Connector google_ads status probe completed.",
    errors: [],
    redacted: true
  }
];

const metricFacts = [
  {
    name: "content_object_count",
    value: 16,
    period: "connector_refresh",
    source_connector: "wordpress_ekologus",
    evidence_id: "ev_refresh_wordpress_inventory",
    unit: null
  },
  {
    name: "merchant_disapproved_product_count",
    value: 3,
    period: "connector_refresh",
    source_connector: "google_merchant_center",
    evidence_id: "ev_refresh_merchant_feed",
    unit: null
  }
];

const metricStoreStatus = {
  backend: "duckdb",
  enabled: true,
  path_configured: false,
  metric_fact_count: 1,
  connector_count: 1,
  refresh_run_count: 1
};

const marketingBrief = {
  generated_at: "2026-06-17T10:00:00Z",
  language: "pl-PL",
  strict_instruction: "WILQ pokazuje tylko metryki z API/evidence.",
  connector_summary: { total: 1, configured: 0, missing_credentials: 1 },
  sections: [
    {
      id: "what_we_know",
      title: "Co wiemy z realnych danych",
      description: "Metric facts.",
      items: [
        {
          id: "brief_metric_wordpress",
          title: "WordPress: content_object_count = 16",
          kind: "metric",
          priority: 21,
          source_connectors: ["wordpress_ekologus"],
          evidence_ids: ["ev_refresh_wordpress_inventory"],
          metric_facts: metricFacts,
          action_ids: [],
          summary: "WILQ ma realne metric facts z connectora WordPress.",
          next_step: "Połącz inventory z GSC/GA4.",
          risk: "low",
          blocker_reason: null
        }
      ]
    },
    {
      id: "what_blocks_us",
      title: "Co blokuje decyzje",
      description: "Blockery.",
      items: []
    },
    {
      id: "safe_next_actions",
      title: "Bezpieczne następne kroki",
      description: "ActionObjects.",
      items: []
    },
    {
      id: "recommended_focus",
      title: "Rekomendowany fokus",
      description: "Priorytety.",
      items: [
        {
          id: "brief_focus_merchant_feed",
          title: "Merchant Center: zacznij od feed/product issues",
          kind: "recommendation",
          priority: 87,
          source_connectors: ["google_merchant_center"],
          evidence_ids: ["ev_refresh_merchant_feed"],
          metric_facts: [metricFacts[1]],
          action_ids: ["act_review_merchant_feed"],
          summary: "WILQ widzi Merchant metric facts i kieruje operatora do walidacji feedu.",
          next_step: "Otwórz payload preview dla action candidate przed zmianą feedu.",
          risk: "medium",
          blocker_reason: null
        }
      ]
    }
  ],
  top_metric_facts: metricFacts,
  evidence_ids: ["ev_refresh_wordpress_inventory"],
  action_ids: ["act_1"],
  blocker_count: 1,
  recommendation_count: 1
};

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
            generated_at: "2026-06-17T10:00:00Z",
            strict_instruction: "No WILQ API evidence means no marketing recommendation.",
            connector_summary: { total: 1, configured: 0, missing_credentials: 1 },
            sections: {
              todays_moves: opportunities,
              money_leaks: opportunities,
              traffic_wins: [],
              content_to_rewrite: [],
              content_to_create: [],
              local_visibility_moves: [],
              social_queue: []
            },
            active_actions: actions,
            connector_health: connectors,
            codex_operator_status: {}
          })
        );
      }
      if (url.endsWith("/api/marketing/brief")) {
        return Promise.resolve(Response.json(marketingBrief));
      }
      if (url.endsWith("/api/connectors")) return Promise.resolve(Response.json(connectors));
      if (url.includes("/api/metrics?")) return Promise.resolve(Response.json(metricFacts));
      if (url.endsWith("/api/metrics/status")) return Promise.resolve(Response.json(metricStoreStatus));
      if (url.endsWith("/api/opportunities")) return Promise.resolve(Response.json(opportunities));
      if (url.endsWith("/api/actions")) return Promise.resolve(Response.json(actions));
      if (url.endsWith("/api/evidence")) return Promise.resolve(Response.json(evidence));
      if (url.endsWith("/api/connectors/refresh-runs")) {
        return Promise.resolve(Response.json(connectorRefreshRuns));
      }
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
  let testQueryClient: QueryClient;

  beforeEach(() => {
    mockFetch();
    testQueryClient = createWilqQueryClient({
      defaultOptions: {
        queries: {
          gcTime: Infinity,
          retry: false
        }
      }
    });
  });

  afterEach(() => {
    cleanup();
    testQueryClient.clear();
    vi.unstubAllGlobals();
  });

  function renderApp(path: string) {
    return render(
      <App
        appRouter={createWilqRouter({ initialPath: path, defaultPendingMinMs: 0 })}
        client={testQueryClient}
      />
    );
  }

  it("command center renders", async () => {
    renderApp("/command-center");
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Command Center" })).toBeInTheDocument()
    );
    expect(screen.getByText("Priorytety dnia")).toBeInTheDocument();
    expect(screen.getByText("Dzisiejszy brief WILQ")).toBeInTheDocument();
    expect(screen.getByText("WordPress: content_object_count = 16")).toBeInTheDocument();
    expect(screen.getByText("Budżet i ryzyko wydatków")).toBeInTheDocument();
    expect(screen.getByText("Kandydaci działań API")).toBeInTheDocument();
  });

  it("connector status renders", async () => {
    renderApp("/command-center");
    await waitFor(() => expect(screen.getByText("Google Ads")).toBeInTheDocument());
    expect(screen.getByText(/GOOGLE_ADS_DEVELOPER_TOKEN/)).toBeInTheDocument();
  });

  it("opportunities route renders", async () => {
    renderApp("/opportunities");
    await waitFor(() =>
      expect(screen.getByText("Google Ads diagnostics blocked until credentials are configured")).toBeInTheDocument()
    );
  });

  it("action detail route renders", async () => {
    renderApp("/actions/act_1");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Odnow Google Ads OAuth refresh token" })
      ).toBeInTheDocument()
    );
  });

  it("missing connector state renders", async () => {
    renderApp("/ads-doctor");
    await waitFor(() => expect(screen.getAllByText("Missing credentials").length).toBeGreaterThan(0));
    expect(screen.getByText("Evidence Registry")).toBeInTheDocument();
    expect(screen.getByText("Connector Refresh Runs")).toBeInTheDocument();
  });

  it("expert rules render on operating routes", async () => {
    renderApp("/ads-doctor/search-terms");
    await waitFor(() => expect(screen.getByText("Expert Rules")).toBeInTheDocument());
    expect(screen.getByText("Search term analysis")).toBeInTheDocument();
  });

  it("workflow route renders persisted workflow runs", async () => {
    renderApp("/workflows");
    await waitFor(() => expect(screen.getByText("Workflow Runs")).toBeInTheDocument());
    expect(screen.getByText("run_daily_command_test")).toBeInTheDocument();
  });

  it("knowledge route renders compiled cards and playbooks", async () => {
    renderApp("/knowledge");
    await waitFor(() => expect(screen.getByText("Knowledge Cards")).toBeInTheDocument());
    expect(screen.getAllByText("Google Ads search diagnostics").length).toBeGreaterThan(0);
    expect(screen.getByText("Machine-Readable Playbooks")).toBeInTheDocument();
  });

  it("merchant route renders WILQ marketing brief feed focus", async () => {
    renderApp("/merchant");
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Merchant Center" })
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Merchant Center: zacznij od feed/product issues")).toBeInTheDocument();
    expect(screen.getAllByText(/ev_refresh_merchant_feed/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/payload preview/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ActionObject/).length).toBeGreaterThan(0);
  });
});
