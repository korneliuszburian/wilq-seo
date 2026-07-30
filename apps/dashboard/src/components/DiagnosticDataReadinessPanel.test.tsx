import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import type { DiagnosticDataReadiness } from "../lib/api";
import { DiagnosticDataReadinessPanel } from "./DiagnosticDataReadinessPanel";

const readyWithObservedZero: DiagnosticDataReadiness = {
  state: "ready",
  state_label: "Dane gotowe do użycia",
  reason: "WILQ potwierdził aktualny odczyt.",
  safe_next_step: "Przejrzyj potwierdzony fakt.",
  connector_id: "localo",
  connector_label: "Localo",
  latest_refresh_id: "refresh_localo_1",
  evidence_ids: ["ev_localo_1"],
  factual_metric_count: 1,
  factual_metrics: [
    {
      name: "localo_competitor_change_count",
      metric_label: "Zmiany konkurencji",
      value: 0,
      period: "localo_mcp_read",
      period_label: "ostatni odczyt Localo",
      source_connector: "localo",
      source_connector_label: "Localo",
      evidence_id: "ev_localo_1",
      dimensions: {},
      dimension_labels: {},
      dimension_value_labels: {},
      unit: null,
      collected_at: null,
      previous_value: null,
      previous_evidence_id: null,
      previous_collected_at: null,
      previous_period: null,
      previous_period_label: null,
      delta: null,
      delta_percent: null,
      trend: "unknown",
      freshness_state: "fresh",
      freshness_label: "dane świeże"
    }
  ],
  coverage_label: "Pokazane metryki są potwierdzone przez WILQ.",
  refresh_allowed: false
};

describe("DiagnosticDataReadinessPanel", () => {
  afterEach(cleanup);

  it("shows an observed zero only when the API marks diagnostic data ready", () => {
    render(<DiagnosticDataReadinessPanel readiness={readyWithObservedZero} />);

    expect(screen.getByText("Zmiany konkurencji: 0")).toBeInTheDocument();
    expect(screen.getAllByText("Źródło: Localo")).toHaveLength(2);
    expect(screen.getByText("Okres: ostatni odczyt Localo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dowód źródłowy" })).toHaveAttribute(
      "href",
      "/evidence/ev_localo_1"
    );
  });

  it("does not turn a configured source without facts into a numeric zero", () => {
    render(
      <DiagnosticDataReadinessPanel
        readiness={{
          ...readyWithObservedZero,
          state: "refresh_available",
          state_label: "Wymagany odczyt danych",
          reason: "Źródło jest skonfigurowane, ale WILQ nie ma utrwalonych metryk.",
          factual_metric_count: 0,
          factual_metrics: [],
          coverage_label: "Brak potwierdzonych metryk do pokazania.",
          refresh_allowed: true
        }}
      />
    );

    expect(screen.getByText("Wymagany odczyt danych")).toBeInTheDocument();
    expect(screen.getByText(/nie ma utrwalonych metryk/)).toBeInTheDocument();
    expect(screen.queryByText("Zmiany konkurencji: 0")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sprawdź źródło danych" })).toHaveAttribute(
      "href",
      "/settings"
    );
  });
});
