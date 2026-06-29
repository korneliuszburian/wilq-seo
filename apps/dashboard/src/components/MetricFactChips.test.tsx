import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricFactChips } from "./MetricFactChips";

describe("MetricFactChips", () => {
  it("renders Localo metric facts with marketer-readable labels", () => {
    render(
      <MetricFactChips
        facts={[
          {
            name: "localo_competitor_change_count",
            metric_label: "Zmiany konkurencji",
            value: 0,
            period: "localo_mcp_read",
            source_connector: "localo",
            evidence_id: "ev_refresh_localo_test",
            dimensions: {
              contract: "competitor_visibility",
              scope: "active_places"
            },
            dimension_labels: {
              contract: "obszar",
              scope: "zakres"
            },
            dimension_value_labels: {
              contract: "widoczność konkurencji",
              scope: "aktywne miejsca"
            },
            unit: null,
            delta: null,
            delta_percent: null,
            trend: "unknown",
            freshness_label: "odświeżone 1h temu"
          }
        ]}
      />
    );

    expect(screen.getByText(/Zmiany konkurencji/)).toBeInTheDocument();
    expect(screen.getByText(/obszar: widoczność konkurencji/)).toBeInTheDocument();
    expect(screen.getByText(/zakres: aktywne miejsca/)).toBeInTheDocument();
    expect(screen.getByText("Dane: odświeżone 1h temu")).toBeInTheDocument();
    expect(screen.queryByText(/ \/ obszar:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/ \/ odświeżone/)).not.toBeInTheDocument();
    expect(screen.queryByText(/metryka WILQ/)).not.toBeInTheDocument();
    expect(screen.queryByText(/localo_competitor_change_count/)).not.toBeInTheDocument();
    expect(screen.queryByText(/competitor_visibility/)).not.toBeInTheDocument();
    expect(screen.queryByText(/active_places/)).not.toBeInTheDocument();
  });

  it("does not translate metric names in React when API label is missing", () => {
    render(
      <MetricFactChips
        facts={[
          {
            name: "localo_total_keyword_volume",
            metric_label: "",
            value: 69420,
            period: "localo_mcp_read",
            source_connector: "localo",
            evidence_id: "ev_refresh_localo_test",
            dimensions: {},
            dimension_labels: {},
            dimension_value_labels: {},
            unit: null,
            delta: null,
            delta_percent: null,
            trend: "unknown",
            freshness_label: ""
          }
        ]}
      />
    );

    expect(screen.getByText(/Metryka bez etykiety/)).toBeInTheDocument();
    expect(screen.queryByText(/Łączny wolumen fraz/)).not.toBeInTheDocument();
    expect(screen.queryByText(/localo_total_keyword_volume/)).not.toBeInTheDocument();
  });

  it("does not translate dimension names or values in React when API labels are missing", () => {
    const { container } = render(
      <MetricFactChips
        facts={[
          {
            name: "localo_competitor_change_count",
            metric_label: "Zmiany konkurencji",
            value: 0,
            period: "localo_mcp_read",
            source_connector: "localo",
            evidence_id: "ev_refresh_localo_test",
            dimensions: {
              contract: "competitor_visibility"
            },
            dimension_labels: {},
            dimension_value_labels: {},
            unit: null,
            delta: null,
            delta_percent: null,
            trend: "unknown",
            freshness_label: ""
          }
        ]}
      />
    );

    expect(within(container).getByText(/Wymiar bez etykiety: wartość do sprawdzenia/)).toBeInTheDocument();
    expect(within(container).queryByText(/obszar: widoczność konkurencji/)).not.toBeInTheDocument();
    expect(within(container).queryByText(/competitor_visibility/)).not.toBeInTheDocument();
  });

  it("keeps metric details as labelled chips instead of slash-combined copy", () => {
    const { container } = render(
      <MetricFactChips
        facts={[
          {
            name: "average_grid_rank",
            metric_label: "średnia pozycja w siatce",
            value: 3,
            period: "localo_mcp_read",
            source_connector: "localo",
            evidence_id: "ev_refresh_localo_test",
            dimensions: {
              contract: "local_rankings",
              scope: "active_places"
            },
            dimension_labels: {
              contract: "obszar",
              scope: "zakres"
            },
            dimension_value_labels: {
              contract: "lokalne pozycje",
              scope: "aktywne miejsca"
            },
            unit: null,
            delta: null,
            delta_percent: null,
            trend: "unknown",
            freshness_label: "odświeżone 8h temu"
          }
        ]}
      />
    );

    expect(within(container).getByText("średnia pozycja w siatce: 3")).toBeInTheDocument();
    expect(within(container).getByText("obszar: lokalne pozycje")).toBeInTheDocument();
    expect(within(container).getByText("zakres: aktywne miejsca")).toBeInTheDocument();
    expect(within(container).getByText("Dane: odświeżone 8h temu")).toBeInTheDocument();
    expect(container.textContent).not.toContain(" / obszar:");
    expect(container.textContent).not.toContain(" / odświeżone");
    expect(container.textContent).not.toContain("3obszar");
    expect(container.textContent).not.toContain("miejscaDane");
  });
});
