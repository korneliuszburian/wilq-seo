import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ContentWorkItemQueueResponse } from "../lib/api";
import { ContentFreshnessBanner } from "./ContentWorkflowBoundaryStates";

function staleAssessment(): ContentWorkItemQueueResponse["freshness_assessment"] {
  return {
    state: "stale",
    state_label: "źródła wymagają odświeżenia",
    checked_at: null,
    stale_after_hours: 48,
    requires_refresh: true,
    missing_connector_ids: [],
    blocked_connector_ids: [],
    stale_connector_ids: ["wordpress_ekologus"],
    connector_labels_requiring_refresh: ["WordPress ekologus.pl"],
    connector_refresh_run_ids: {},
    connector_covered_windows: {},
    connector_settlement_states: {},
    connector_quality_states: {},
    connector_quality_caveats: {},
    summary: "WordPress wymaga odświeżenia.",
    next_step: "Odśwież źródło przed pracą."
  };
}

describe("content source refresh control", () => {
  it("exposes only eligible stale sources and delegates a read-only refresh", () => {
    const onRefresh = vi.fn();
    render(
      <ContentFreshnessBanner
        assessment={staleAssessment()}
        refresh={{
          eligibleConnectorIds: ["wordpress_ekologus"],
          activeConnectorId: null,
          runs: {},
          errors: {},
          onRefresh
        }}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Odśwież WordPress" }));
    expect(onRefresh).toHaveBeenCalledWith("wordpress_ekologus");
  });
});
