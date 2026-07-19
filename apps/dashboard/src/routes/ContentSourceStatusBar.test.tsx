import { describe, expect, it } from "vitest";

import { contentSourceStatusItems } from "./ContentSourceStatusBar";

describe("contentSourceStatusItems", () => {
  it("renders only lineage-bound sources and preserves stale/blocked state", () => {
    const items = contentSourceStatusItems({
      preflight: { item: { source_connectors: ["google_search_console", "google_ads", "ahrefs"] } },
      freshnessAssessment: {
        stale_connector_ids: ["google_ads"],
        blocked_connector_ids: [],
      }
    } as never);

    expect(items.map((item) => [item.id, item.status])).toEqual([
      ["google_search_console", "w dowodach"],
      ["google_ads", "wymaga odświeżenia"],
      ["ahrefs", "w dowodach"]
    ]);
  });
});
