import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { merchantDiagnostics } from "./merchantDiagnostic.fixture";
import type { ActionObject } from "../lib/api";
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
    getMerchantDiagnostics: vi.fn().mockResolvedValue(merchantDiagnostics),
    getActions: vi.fn().mockResolvedValue([merchantAction])
  };
});

describe("MerchantDiagnosticSurface", () => {
  it("gives the marketer a safe Merchant decision before technical details", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MerchantDiagnosticSurface />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "Produkty" })).toBeInTheDocument());
    expect(screen.getByText("Najważniejsza praca teraz")).toBeInTheDocument();
    expect(screen.getByText("Co blokuje decyzję")).toBeInTheDocument();
    expect(screen.getByText("Kolejka problemów produktów")).toBeInTheDocument();
    expect(screen.getAllByText(/dane do odświeżenia/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/automatyczna zmiana pliku produktowego/).length).toBeGreaterThan(0);
    expect(screen.queryByText("act_review_merchant_feed_issues")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd Merchant" }));
    expect(screen.getByText("Pełny przegląd Merchant")).toBeInTheDocument();
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
});
