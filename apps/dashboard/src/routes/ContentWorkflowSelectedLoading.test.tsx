import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ContentWorkItemQueueCandidate, ContentWorkItemQueueResponse } from "../lib/api";
import { ContentWorkflowSelectedLoading } from "./ContentWorkflowBoundaryStates";

const freshness = {
  state: "fresh",
  state_label: "dane treści świeże",
  checked_at: null,
  stale_after_hours: 48,
  requires_refresh: false,
  missing_connector_ids: [],
  blocked_connector_ids: [],
  stale_connector_ids: [],
  connector_labels_requiring_refresh: [],
  connector_refresh_run_ids: {},
  connector_covered_windows: {},
  connector_settlement_states: {},
  connector_quality_states: {},
  connector_quality_caveats: {},
  summary: "Dane są dostępne.",
  next_step: "Sprawdź plan."
} as ContentWorkItemQueueResponse["freshness_assessment"];

describe("ContentWorkflowSelectedLoading", () => {
  it("keeps live queue metrics visible while the heavy snapshot loads", () => {
    const candidate = {
      work_item_id: "content_work_item_outsourcing",
      decision_id: "decision_outsourcing",
      title: "Doradztwo środowiskowe",
      topic: "Doradztwo środowiskowe",
      priority: 1,
      recommended_mode: "refresh",
      recommended_mode_label: "odśwież istniejącą treść",
      status_label: "gotowe do planu",
      reason: "Strona ma dokładne dane z wyszukiwarki.",
      evidence_ids: ["ev_gsc_outsourcing"],
      source_connectors: ["google_search_console"],
      source_connector_labels: ["Google Search Console"],
      action_ids: [],
      action_summary_label: "",
      source_public_url: "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
      final_canonical_url: "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
      intended_final_url: "https://www.ekologus.pl/oferta/doradztwo-i-outsourcing-ekologiczny/",
      preview_url: null,
      preflight_status: "plan_allowed",
      preflight_status_label: "można planować",
      duplicate_canonical_risk_summary: "Adres jest dokładnie powiązany.",
      measurement_readiness: {
        status: "ready_to_plan",
        label: "pomiar do zaplanowania",
        reason: "Dane bazowe są dostępne.",
        source_connectors: ["google_search_console"]
      },
      search_metrics: {
        impressions: 62,
        clicks: 0,
        ctr: 0,
        best_average_position: 1,
        query_count: 30,
        primary_query: "doradztwo z zakresu ochrony środowiska",
        comparison_status: "not_available",
        comparison_reason: "Brakuje dwóch okresów.",
        comparison_periods: [],
        comparison_evidence_ids: []
      },
      safe_next_step: "Sprawdź dopasowaną usługę.",
      freshness_assessment: freshness,
      blockers: []
    } as ContentWorkItemQueueCandidate;

    render(<ContentWorkflowSelectedLoading assessment={freshness} candidate={candidate} />);

    expect(screen.getByTestId("content-queue-metrics")).toHaveTextContent(
      "62 wyświetleń · 0 kliknięć · CTR 0.00%"
    );
    expect(screen.getByText(/doradztwo z zakresu ochrony środowiska/)).toBeInTheDocument();
  });
});
