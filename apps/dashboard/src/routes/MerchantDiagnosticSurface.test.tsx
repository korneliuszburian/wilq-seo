import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { merchantDiagnostics } from "./merchantDiagnostic.fixture";
import { getActions, getMerchantDiagnostics, type ActionObject } from "../lib/api";
import { MerchantDiagnosticSurface } from "./MerchantDiagnosticSurface";

const merchantAction = vi.hoisted(() => ({
  id: "act_review_merchant_feed_issues",
  title: "Przygotuj kolejkę przeglądu pliku produktowego Merchant Center",
  domain: "merchant",
  connector: "google_merchant_center",
  mode: "prepare",
  mode_label: "przygotowanie",
  risk: "medium",
  risk_label: "średnie ryzyko",
  status: "needs_validation",
  status_label: "do sprawdzenia",
  evidence_ids: ["ev_refresh_merchant_feed"],
  evidence_summary_label: "1 dowód źródłowy",
  metrics: [],
  human_diagnosis: "Plik produktowy wymaga ręcznego sprawdzenia.",
  recommended_reason: "WILQ ma dowód z Merchant Center.",
  validation_status: "not_validated",
  validation_status_label: "niezwalidowana",
  review_gate: { apply_allowed: false, apply_blocker_labels: ["Brak przeglądu operatora"] },
  preview_cards: [],
  payload: { action_type: "merchant_feed_issue" },
  audit_events: []
} as unknown as ActionObject));

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getMerchantDiagnostics: vi.fn(),
    getActions: vi.fn()
  };
});

describe("MerchantDiagnosticSurface", () => {
  beforeEach(() => {
    vi.mocked(getMerchantDiagnostics).mockReset();
    vi.mocked(getActions).mockReset();
    vi.mocked(getMerchantDiagnostics).mockResolvedValue(merchantDiagnostics as never);
    vi.mocked(getActions).mockResolvedValue([merchantAction]);
  });

  it("does not present stale Merchant counts as a current decision", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MerchantDiagnosticSurface />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "Produkty" })).toBeInTheDocument());
    expect(screen.getByText("Dane wymagają odświeżenia")).toBeInTheDocument();
    expect(screen.getByText(/nie używa go jako bieżącej podstawy decyzji/)).toBeInTheDocument();
    expect(screen.queryByText("Najważniejsza praca teraz")).not.toBeInTheDocument();
    expect(screen.queryByText("10 900")).not.toBeInTheDocument();
    expect(screen.queryByText("act_review_merchant_feed_issues")).not.toBeInTheDocument();
  });

  it("keeps the Merchant operator contract typed and disclosure-safe", () => {
    const routeSource = readFileSync("src/routes/MerchantDiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("summary.action_summary_label");
    expect(routeSource).toContain("decision.action_summary_label");
    expect(routeSource).toContain("merchantDecisionQueueTitle");
    expect(routeSource).not.toContain("sample_titles.slice(0, 2).join");
    expect(routeSource).toContain("cluster.reported_issue_summary_label");
    expect(routeSource).toContain("row.ads_clicks_label");
    expect(routeSource).toContain("row.ga4_ecommerce_purchases_label");
    expect(routeSource).toContain("row.ga4_purchase_revenue_label");
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain('empty="brak');
    expect(routeSource).not.toContain('row.ads_clicks ?? "brak"');
    expect(routeSource).not.toContain('row.ga4_ecommerce_purchases ?? "brak"');
    expect(routeSource).not.toContain('row.ga4_purchase_revenue ?? "brak"');
    expect(routeSource).toContain("nie oceniaj gotowości połączenia");
    expect(routeSource).toContain("bez odczytu Merchant");
    expect(routeSource).not.toContain("{decision.decision_type_label} /");
    expect(routeSource).not.toContain(" / ${cluster.reporting_context_label}");
    expect(routeSource).not.toContain("formatMerchantIdCount");
    expect(routeSource).not.toContain("function formatPolishCount");
    expect(routeSource).not.toContain("cluster.product_count,");
    expect(routeSource).not.toContain("{item.intent_label} / {item.priority_label}");
  });

  it("does not turn an unknown product count into zero when another Merchant fact is ready", async () => {
    const readyWithoutProductCount = structuredClone(merchantDiagnostics) as Record<string, unknown>;
    readyWithoutProductCount.product_count = null;
    readyWithoutProductCount.data_readiness = {
      ...merchantDiagnostics.data_readiness,
      state: "ready",
      factual_metric_count: 1,
      factual_metrics: [
        {
          name: "issue_product_count",
          metric_label: "Zgłoszenia problemów",
          value: 23,
          period: "connector_refresh",
          period_label: "ostatni odczyt źródła",
          source_connector: "google_merchant_center",
          source_connector_label: "Merchant Center",
          evidence_id: "ev_ready_issue_count"
        }
      ],
      coverage_label: "Potwierdzona jest tylko liczba zgłoszeń.",
      refresh_allowed: false
    };
    vi.mocked(getMerchantDiagnostics).mockResolvedValue(readyWithoutProductCount as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MerchantDiagnosticSurface />
      </QueryClientProvider>
    );

    await screen.findByRole("heading", { name: "Produkty" });
    expect(screen.queryByText("produktów w ostatnim odczycie")).not.toBeInTheDocument();
  });

  it("shows an observed zero product count only through its exact Merchant fact", async () => {
    const readyWithObservedZero = structuredClone(merchantDiagnostics) as Record<string, unknown>;
    readyWithObservedZero.product_count = 0;
    readyWithObservedZero.data_readiness = {
      ...merchantDiagnostics.data_readiness,
      state: "ready",
      factual_metric_count: 1,
      factual_metrics: [
        {
          name: "total_products",
          metric_label: "produkty w pliku produktowym",
          value: 0,
          period: "connector_refresh",
          period_label: "ostatni odczyt źródła",
          source_connector: "google_merchant_center",
          source_connector_label: "Merchant Center",
          evidence_id: "ev_observed_zero_products"
        }
      ],
      coverage_label: "Potwierdzona liczba produktów.",
      refresh_allowed: false
    };
    vi.mocked(getMerchantDiagnostics).mockResolvedValue(readyWithObservedZero as never);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <MerchantDiagnosticSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByText("produktów w ostatnim odczycie")).toBeInTheDocument();
    expect(screen.getAllByText(/Źródło: Merchant Center/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Okres: ostatni odczyt źródła/).length).toBeGreaterThan(0);
  });
});
