import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import type { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App, createWilqQueryClient, createWilqRouter } from "./App";

const opportunities = [
  {
    id: "opp_decision_review_ads_campaign_metrics",
    type: "google_ads_review_queue",
    title: "Przejrzyj kolejki Ads do oceny bez apply",
    domain: "google_ads",
    source_connectors: ["google_ads"],
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metric_tiles: {
      kampanie: 18,
      zapytania: 50,
      "podgląd budżetu": 18,
      rekomendacje: 4
    },
    metrics: [],
    human_diagnosis:
      "Google Ads ma liczniki do oceny i ActionObjecty review-only. Apply pozostaje zablokowany.",
    recommended_action:
      "Otwórz /ads-doctor i przejrzyj kolejno: podgląd budżetów, podgląd rekomendacji, przegląd wykluczeń i podgląd segmentów.",
    risk: "medium",
    action_ids: [
      "act_prepare_ads_campaign_review_queue",
      "act_prepare_google_ads_recommendation_review_queue"
    ],
    expert_rule_ids: [],
    playbook_ids: ["wilq-ads-doctor"],
    is_fixture: false
  }
];

const actions = [
  {
    id: "act_prepare_ads_campaign_review_queue",
    title: "Przygotuj kolejkę review kampanii Ads",
    domain: "google_ads",
    connector: "google_ads",
    mode: "prepare",
    risk: "medium",
    status: "needs_validation",
    evidence_ids: ["ev_refresh_refresh_google_ads_test"],
    metrics: [],
    validation_status: "not_validated",
    human_diagnosis: "Google Ads ma kampanie do review.",
    recommended_reason: "Przygotuj review-only queue bez apply.",
    payload: {
      action_type: "google_ads_campaign_review",
      connector: "google_ads",
      mode: "prepare_only",
      destructive: false
    },
    audit_events: []
  }
];

const evidence = [
  {
    id: "ev_refresh_refresh_google_ads_test",
    source_connector: "google_ads",
    source_type: "connector_refresh",
    source_id: "refresh_google_ads_test",
    collected_at: "2026-06-17T10:00:00Z",
    freshness: { state: "fresh" },
    summary: "Google Ads vendor read completed with sanitized campaign counters.",
    raw_ref: null
  }
];

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
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

  it("opportunities route renders", async () => {
    renderOpportunities();
    await waitFor(() =>
      expect(screen.getByText("Przejrzyj kolejki Ads do oceny bez apply")).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: "Szanse i decyzje" })).toBeInTheDocument();
    expect(screen.getByText("Kolejka decyzji z WILQ API")).toBeInTheDocument();
    expect(screen.getAllByText("kampanie").length).toBeGreaterThan(0);
    expect(screen.getAllByText("podgląd budżetu").length).toBeGreaterThan(0);
    expect(screen.getByText("Aktywne")).toBeInTheDocument();
    const opportunityCard = screen
      .getByText("Przejrzyj kolejki Ads do oceny bez apply")
      .closest("article");
    expect(opportunityCard).not.toBeNull();
    const card = within(opportunityCard as HTMLElement);
    expect(card.getByText("Dowody: 1 ID")).toBeInTheDocument();
    expect(card.getByText("Akcje: 2")).toBeInTheDocument();
    expect(card.queryByText(/ev_refresh_refresh_google_ads_test/)).not.toBeInTheDocument();
    expect(card.queryByText(/Playbooki:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Rejestr kart opportunities")).not.toBeInTheDocument();
    expect(screen.getByText("Dowody użyte przez karty")).toBeInTheDocument();
    expect(screen.queryByText("Evidence użyte przez opportunities")).not.toBeInTheDocument();
  });

  it("shows the primary decision queue while secondary registries are still loading", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/opportunities")) {
          return Promise.resolve(Response.json(opportunities));
        }
        if (url.endsWith("/api/actions") || url.endsWith("/api/evidence")) {
          return new Promise<Response>(() => {});
        }
        return Promise.resolve(Response.json({}));
      })
    );

    renderOpportunities();

    await waitFor(() =>
      expect(screen.getByText("Przejrzyj kolejki Ads do oceny bez apply")).toBeInTheDocument()
    );
    expect(screen.getByRole("heading", { name: "Szanse i decyzje" })).toBeInTheDocument();
    expect(screen.getByText("Kolejka decyzji z WILQ API")).toBeInTheDocument();
    expect(screen.getByText("Powiązane akcje")).toBeInTheDocument();
    expect(screen.getByText("Dowody użyte przez karty")).toBeInTheDocument();
    expect(screen.getAllByText("Ładowanie stanu WILQ API").length).toBeGreaterThan(0);
  });
});
