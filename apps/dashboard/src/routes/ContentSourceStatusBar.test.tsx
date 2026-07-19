import { describe, expect, it } from "vitest";

import { contentSourceStatusItems } from "./ContentSourceStatusBar";

describe("contentSourceStatusItems", () => {
  it("renders only lineage-bound sources and preserves stale/blocked state", () => {
    const items = contentSourceStatusItems({
      preflight: {
        item: {
          source_connectors: ["google_search_console", "google_ads", "ahrefs"],
          total_impressions: 266,
          total_clicks: 1,
          aggregate_ctr: 0.0037593985
        }
      },
      freshnessAssessment: {
        stale_connector_ids: ["google_ads"],
        blocked_connector_ids: [],
      }
    } as never);

    expect(items.map((item) => [item.id, item.status])).toEqual([
      ["google_search_console", "266 wyśw. · 1 klik. · CTR 0.38%"],
      ["google_ads", "wymaga odświeżenia"],
      ["ahrefs", "w dowodach"]
    ]);
  });
});
