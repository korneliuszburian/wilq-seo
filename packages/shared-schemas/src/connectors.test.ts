import { describe, expect, it } from "vitest";

import { DiagnosticDataReadinessSchema } from "./connectors";

const observedZero = {
  name: "localo_competitor_change_count",
  metric_label: "Zmiany konkurencji",
  value: 0,
  period: "localo_mcp_read",
  period_label: "ostatni odczyt Localo",
  source_connector: "localo",
  source_connector_label: "Localo",
  evidence_id: "ev_localo_observed_zero"
};

describe("DiagnosticDataReadinessSchema", () => {
  it("accepts an observed zero only in a factual ready state", () => {
    expect(
      DiagnosticDataReadinessSchema.safeParse({
        state: "ready",
        state_label: "Dane gotowe do użycia",
        reason: "WILQ potwierdził fakt.",
        safe_next_step: "Przejrzyj fakt.",
        connector_id: "localo",
        connector_label: "Localo",
        latest_refresh_id: "refresh_localo_1",
        evidence_ids: ["ev_localo_observed_zero"],
        factual_metric_count: 1,
        factual_metrics: [observedZero],
        coverage_label: "Pokazane metryki są potwierdzone przez WILQ.",
        refresh_allowed: false
      }).success
    ).toBe(true);
  });

  it("rejects a non-ready state that tries to present a metric as a fact", () => {
    expect(
      DiagnosticDataReadinessSchema.safeParse({
        state: "refresh_available",
        state_label: "Wymagany odczyt danych",
        reason: "Brak odczytu.",
        safe_next_step: "Uruchom odczyt.",
        connector_id: "localo",
        connector_label: "Localo",
        evidence_ids: [],
        factual_metric_count: 1,
        factual_metrics: [observedZero],
        coverage_label: "Brak potwierdzonych metryk.",
        refresh_allowed: true
      }).success
    ).toBe(false);
  });

  it("rejects a ready fact without evidence lineage or marketer labels", () => {
    for (const field of ["evidence_id", "metric_label", "period_label", "source_connector_label"] as const) {
      const invalidFact = { ...observedZero, [field]: "   " };
      expect(
        DiagnosticDataReadinessSchema.safeParse({
          state: "ready",
          state_label: "Dane gotowe do użycia",
          reason: "WILQ potwierdził fakt.",
          safe_next_step: "Przejrzyj fakt.",
          connector_id: "localo",
          connector_label: "Localo",
          evidence_ids: ["ev_localo_observed_zero"],
          factual_metric_count: 1,
          factual_metrics: [invalidFact],
          coverage_label: "Pokazane metryki są potwierdzone przez WILQ.",
          refresh_allowed: false
        }).success
      ).toBe(false);
    }
  });
});
