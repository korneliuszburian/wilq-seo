import { describe, expect, it } from "vitest";

import {
  resolvedPageSectionCount,
  summarizeContentSourceQuality
} from "./ContentWorkflowJourneyContext";

describe("resolvedPageSectionCount", () => {
  it("uses the fresh preflight inventory instead of a stale queue projection", () => {
    expect(resolvedPageSectionCount(7, 1)).toBe(7);
  });

  it("falls back to the queue count only when preflight has no count", () => {
    expect(resolvedPageSectionCount(null, 4)).toBe(4);
    expect(resolvedPageSectionCount(undefined, null)).toBeNull();
  });
});

describe("summarizeContentSourceQuality", () => {
  it("keeps partial and unverified sources visible even when freshness is fresh", () => {
    expect(
      summarizeContentSourceQuality({
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
        connector_settlement_states: { google_analytics_4: "settling" },
        connector_quality_states: {
          google_search_console: "partial",
          wordpress_ekologus: "unverified",
          google_analytics_4: "unverified",
          ahrefs: "unknown"
        },
        connector_quality_caveats: {},
        summary: "Podstawowe dane są świeże.",
        next_step: "Można użyć danych do review."
      })
    ).toEqual(["GSC: odczyt częściowy", "WordPress: jakość do sprawdzenia", "GA4: jakość do sprawdzenia"]);
  });

  it("does not add a caveat when every available source is verified", () => {
    expect(
      summarizeContentSourceQuality({
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
        connector_quality_states: { google_search_console: "verified" },
        connector_quality_caveats: {},
        summary: "Podstawowe dane są świeże.",
        next_step: "Można użyć danych do review."
      })
    ).toEqual([]);
  });
});
