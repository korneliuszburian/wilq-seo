import { describe, expect, it } from "vitest";

import { inventoryDispositionLabel, planningScopeSummary } from "./ContentPlanningReviewPanel";

describe("inventoryDispositionLabel", () => {
  it("keeps inventory actions concrete and Polish", () => {
    expect(inventoryDispositionLabel("preserve")).toBe("zachowaj");
    expect(inventoryDispositionLabel("merge")).toBe("scal po review");
    expect(inventoryDispositionLabel("rewrite")).toBe("przepisz");
    expect(inventoryDispositionLabel("create")).toBe("utwórz");
  });
});

describe("planningScopeSummary", () => {
  it("separates document sections from inventory rows needing review", () => {
    expect(
      planningScopeSummary([
        { inventory_disposition: "rewrite" },
        { inventory_disposition: "merge" },
        { inventory_disposition: "remove_review_required" }
      ])
    ).toBe("2 sekcje trafi do pełnego tekstu · 1 element pozostaje do osobnego review");
  });
});
