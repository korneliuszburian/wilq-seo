import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, createWilqQueryClient, createWilqRouter } from "./App";

const opportunities = [
  {
    id: "opp_decision_review_ads_campaign_metrics",
    type: "google_ads_review_queue",
    title: "Przejrzyj kolejki Ads do oceny bez zapisu zmian",
    domain: "google_ads",
    source_connectors: ["google_ads"],
    source_connector_labels: ["Google Ads"],
    source_connector_summary_label: "Google Ads",
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    evidence_summary_label: "1 dowód źródłowy",
    metric_tiles: {
      kampanie: 18,
      zapytania: 50,
      "podgląd budżetu": 18,
      rekomendacje: 4
    },
    metrics: [
      {
        name: "clicks",
        value: 42,
        period: "last_28d",
        source_connector: "google_ads",
        evidence_id: "ev_refresh_refresh_google_ads_test",
        dimensions: { campaign_name: "Ekologus Ogólna" },
        unit: null,
        collected_at: "2026-06-17T10:00:00Z",
        previous_value: null,
        delta: null,
        delta_percent: null,
        trend: "unknown",
        freshness_state: "fresh",
        freshness_label: "świeże"
      }
    ],
    human_diagnosis:
      "Google Ads ma liczniki do oceny i akcje do sprawdzenia. Zapis zmian pozostaje zablokowany.",
    recommended_action:
      "Otwórz /ads-doctor i przejrzyj kolejno: podgląd budżetów, podgląd rekomendacji, przegląd wykluczeń i podgląd segmentów.",
    risk: "medium",
    action_ids: [
      "act_prepare_ads_campaign_review_queue",
      "act_prepare_google_ads_recommendation_review_queue"
    ],
    action_summary_label: "2 akcje do sprawdzenia",
    expert_rule_ids: [],
    playbook_ids: ["wilq-ads-doctor"],
    knowledge_summary_label: "1 playbook",
    is_fixture: false
  }
];

const actions = [
  {
    id: "act_prepare_ads_campaign_review_queue",
    title: "Przygotuj kolejkę przeglądu kampanii Ads",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis: "Google Ads ma kampanie do sprawdzenia.",
    recommended_reason: "Przygotuj kolejkę do sprawdzenia bez zapisu zmian.",
    payload: {
      action_type: "google_ads_campaign_review",
      connector: "google_ads",
      mode: "prepare_only",
      destructive: false
    },
    audit_events: []
  }
];


const commandCenter = {
  generated_at: "2026-06-22T18:56:00Z",
  strict_instruction: "WILQ pokazuje tylko metryki z danych źródłowych.",
  primary_next_step: "Najpierw sprawdź kolejkę.",
  blocker_count: 1,
  tactical_item_count: 2,
  source_connectors: ["google_ads", "google_search_console"],
  source_connector_labels: ["Google Ads", "Google Search Console"],
  evidence_ids: ["ev_refresh_refresh_google_ads_test"],
  evidence_summary: "1 dowód źródłowy",
  action_ids: ["act_prepare_ads_campaign_review_queue"],
  action_summary: "1 akcja do sprawdzenia",
  daily_decisions: [],
  work_orders: [
    {
      id: "work_order_ads_review",
      title: "Sprawdź wykluczenia w Google Ads",
      status: "review_required",
      status_label: "Wymaga review",
      owner_role: "ads_analytics",
      priority: 1,
      domain: "google_ads",
      route: "/ads-doctor",
      route_label: "Reklamy",
      summary: "Wyszukiwane hasła i wykluczenia wymagają oceny operatora.",
      why_it_matters: "Wykluczenia mogą zablokować dobry ruch, więc potrzebują review przed zmianą.",
      next_safe_step: "Otwórz Google Ads i sprawdź wykluczenia.",
      close_condition: "Zamknięte po review bezpiecznej akcji w WILQ.",
      source_connectors: ["google_ads"],
      source_connector_labels: ["Google Ads"],
      evidence_ids: ["ev_refresh_refresh_google_ads_test"],
      evidence_summary: "1 dowód źródłowy",
      action_ids: ["act_prepare_ads_campaign_review_queue"],
      action_summary: "1 akcja do sprawdzenia",
      blocked_claims: ["ROAS"],
      blocked_claim_labels: ["ROAS"],
      freshness: { state: "fresh" },
      freshness_label: "świeże dane",
      risk: "high",
      decision_id: "decision_ads_review"
    }
  ],
  operator_brief: [],
  demo_script: [],
  action_plan: [],
  connector_summary: {
    total: 2,
    configured: 2,
    missing_credentials: 0,
    missing_credential_connectors: [],
    stale: 0,
    stale_connectors: [],
    blocked: 0,
    blocked_connectors: []
  },
  sections: {},
  active_actions: [],
  connector_health: [],
  codex_operator_status: {}
};

const evidence = [
  {
    id: "ev_refresh_refresh_google_ads_test",
    source_connector: "google_ads",
    source_type: "connector_refresh",
    source_id: "refresh_google_ads_test",
    collected_at: "2026-06-17T10:00:00Z",
    freshness: { state: "fresh" },
    summary: "Odczyt Google Ads zakończony z oczyszczonymi licznikami kampanii.",
    raw_ref: null
  }
];

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/dashboard/command-center")) return Promise.resolve(Response.json(commandCenter));
      if (url.endsWith("/api/opportunities")) return Promise.resolve(Response.json(opportunities));
      if (url.endsWith("/api/actions")) return Promise.resolve(Response.json(actions));
      if (url.endsWith("/api/evidence")) return Promise.resolve(Response.json(evidence));
      return Promise.resolve(Response.json({}));
    })
  );
}

describe("Opportunities route", () => {
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

  function renderOpportunities() {
    return render(
      <App
        appRouter={createWilqRouter({ initialPath: "/opportunities", defaultPendingMinMs: 0 })}
        client={testQueryClient}
      />
    );
  }


  it("opportunities route renders as the unified Kolejka", async () => {
    renderOpportunities();
    await waitFor(() => expect(screen.queryByText("Ładowanie stanu WILQ")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Kolejka" })).toBeInTheDocument();
    expect(screen.getByText("Jedna wspólna kolejka decyzji, blokad i bezpiecznych następnych kroków. Tu nie ma drugiego raportu: to lista pracy do przejścia.")).toBeInTheDocument();
    expect(screen.getByText("wszystkie pozycje")).toBeInTheDocument();
    expect(screen.getByText("gotowe do sprawdzenia")).toBeInTheDocument();
    expect(screen.getByText("wymaga review")).toBeInTheDocument();
    expect(screen.getByText("zablokowane")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Wszystkie/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Priorytet P1/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tylko blokady" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tylko gotowe" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kolejka decyzji i akcji" })).toBeInTheDocument();
    expect(await screen.findByText("Sprawdź wykluczenia w Google Ads")).toBeInTheDocument();
    expect(screen.getByText("Przejrzyj kolejki Ads do oceny bez zapisu zmian")).toBeInTheDocument();
    expect(screen.getAllByText("Reklamy").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1 dowód źródłowy").length).toBeGreaterThan(0);
    expect(screen.getByText("wysokie")).toBeInTheDocument();
    expect(screen.getAllByText("Wymaga review").length).toBeGreaterThan(0);
    expect(screen.getByText("Ostatnio zakończone")).toBeInTheDocument();
    expect(screen.queryByText("Kolejka decyzji z WILQ")).not.toBeInTheDocument();
    expect(screen.queryByText("Dowody użyte przez karty")).not.toBeInTheDocument();
    expect(screen.queryByText("Powiązane akcje")).not.toBeInTheDocument();
    expect(screen.queryByText("Rejestr kart opportunities")).not.toBeInTheDocument();
    expect(screen.queryByText(/google_ads \/ google_ads_review_queue/)).not.toBeInTheDocument();
  });



  it("shows the queue table while actions are still loading", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/dashboard/command-center")) {
          return Promise.resolve(Response.json(commandCenter));
        }
        if (url.endsWith("/api/opportunities")) {
          return Promise.resolve(Response.json(opportunities));
        }
        if (url.endsWith("/api/actions")) {
          return new Promise<Response>(() => {});
        }
        if (url.endsWith("/api/evidence")) return Promise.resolve(Response.json(evidence));
        return Promise.resolve(Response.json({}));
      })
    );

    renderOpportunities();

    await waitFor(() =>
      expect(screen.getByText("Sprawdź wykluczenia w Google Ads")).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: "Kolejka" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Kolejka decyzji i akcji" })).toBeInTheDocument();
    expect(screen.queryByText("Powiązane akcje")).not.toBeInTheDocument();
    expect(screen.queryByText("Dowody użyte przez karty")).not.toBeInTheDocument();
  });


  it("renders opportunity detail metrics as a summary before technical details", async () => {
    render(
      <App
        appRouter={createWilqRouter({
          initialPath: "/opportunities/opp_decision_review_ads_campaign_metrics",
          defaultPendingMinMs: 0
        })}
        client={testQueryClient}
      />
    );

    await waitFor(() =>
      expect(screen.getByText("Przejrzyj kolejki Ads do oceny bez zapisu zmian")).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: "Metryki z dowodów" })).toBeInTheDocument();
    expect(screen.getByText(/kampanie: 18/)).toBeInTheDocument();
    expect(screen.getByText("Pokaż szczegóły techniczne metryk")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Metryki techniczne" })).not.toBeInTheDocument();
    expect(screen.queryByText(/"name": "clicks"/)).not.toBeInTheDocument();
  });
});
