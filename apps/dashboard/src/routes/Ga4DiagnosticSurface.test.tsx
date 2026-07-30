import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getActions, getGa4Diagnostics, type ActionObject } from "../lib/api";
import { ga4Diagnostics } from "./ga4Diagnostics.fixture";
import { Ga4DiagnosticSurface } from "./Ga4DiagnosticSurface";

const ga4Action = vi.hoisted(() => ({
  id: "act_review_ga4_tracking_quality",
  title: "Sprawdź jakość pomiaru GA4 przed oceną kampanii",
  domain: "ga4",
  connector: "google_analytics_4",
  mode: "review",
  mode_label: "do sprawdzenia",
  risk: "medium",
  risk_label: "średnie ryzyko",
  status: "needs_validation",
  status_label: "do sprawdzenia",
  evidence_ids: ["ev_refresh_ga4"],
  evidence_summary_label: "1 dowód źródłowy",
  metrics: [],
  human_diagnosis: "Pomiar GA4 wymaga kontroli.",
  recommended_reason: "WILQ ma dowód z GA4.",
  validation_status: "not_validated",
  validation_status_label: "niezwalidowana",
  review_gate: { apply_allowed: false, apply_blocker_labels: ["Brak przeglądu operatora"] },
  preview_cards: [],
  payload: { action_type: "review" },
  audit_events: []
} as unknown as ActionObject));

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getGa4Diagnostics: vi.fn(),
    getActions: vi.fn()
  };
});

describe("Ga4DiagnosticSurface", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.mocked(getGa4Diagnostics).mockReset();
    vi.mocked(getActions).mockReset();
    vi.mocked(getGa4Diagnostics).mockResolvedValue(ga4Diagnostics as never);
    vi.mocked(getActions).mockResolvedValue([ga4Action]);
  });

  it("gives the marketer a safe measurement decision before technical details", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <Ga4DiagnosticSurface />
      </QueryClientProvider>
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "GA4" })).toBeInTheDocument());
    expect(screen.getByText("GA4: co dziś zrobić")).toBeInTheDocument();
    expect(screen.getByText("Najpierw pomiar")).toBeInTheDocument();
    expect(screen.getByText("362")).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
    expect(screen.getAllByText(/dane świeże/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/konwersji/).length).toBeGreaterThan(0);
    expect(screen.queryByText("google_analytics_4")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Pokaż pełny przegląd GA4" }));
    expect(screen.getByText("Problemy pomiaru GA4")).toBeInTheDocument();
  });

  it("keeps the GA4 measurement contract typed and review-only", () => {
    const routeSource = readFileSync("src/routes/Ga4DiagnosticSurface.tsx", "utf8");
    expect(routeSource).toContain("action.preview_cards");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("data.evidence_summary_label");
    expect(routeSource).toContain("conversionReadiness.missing_read_contract_summary_label");
    expect(routeSource).toContain(
      "WILQ nie podał etykiety akcji; nie traktuj tej decyzji jako gotowej do działania"
    );
    expect(routeSource).not.toContain('empty="brak"');
    expect(routeSource).not.toContain("values={conversionReadiness.missing_read_contract_labels}");
    expect(routeSource).not.toContain("liczba akcji do sprawdzenia");
    expect(routeSource).not.toContain("action.payload.payload_preview");
    expect(routeSource).not.toContain("function formatGa4EvidenceCount");
    expect(routeSource).not.toContain("function formatGa4ActionCount");
  });

  it("keeps GA4 readiness authoritative when the secondary actions read is pending", async () => {
    const blockedDiagnostics = structuredClone(ga4Diagnostics);
    blockedDiagnostics.data_readiness = {
      ...blockedDiagnostics.data_readiness,
      state: "blocked",
      state_label: "Odczyt GA4 zablokowany",
      reason: "Dokładny powód GA4 z API.",
      safe_next_step: "Dokładny bezpieczny krok GA4 z API.",
      factual_metric_count: 0,
      factual_metrics: [],
      coverage_label: "Brak potwierdzonych metryk GA4."
    };
    vi.mocked(getGa4Diagnostics).mockResolvedValue(blockedDiagnostics as never);
    vi.mocked(getActions).mockImplementation(() => new Promise(() => {}));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <Ga4DiagnosticSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByText("Dokładny powód GA4 z API.")).toBeInTheDocument();
    expect(screen.getByText("Dokładny bezpieczny krok GA4 z API.")).toBeInTheDocument();
    expect(screen.queryByText("Nie udało się pobrać akcji do sprawdzenia.")).not.toBeInTheDocument();
    expect(screen.queryByText("GA4: co dziś zrobić")).not.toBeInTheDocument();
  });
});
