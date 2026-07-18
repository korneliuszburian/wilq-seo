import { describe, expect, it } from "vitest";

import { inventoryDispositionLabel } from "./ContentPlanningReviewPanel";

describe("inventoryDispositionLabel", () => {
  it("keeps inventory actions concrete and Polish", () => {
    expect(inventoryDispositionLabel("preserve")).toBe("zachowaj");
    expect(inventoryDispositionLabel("merge")).toBe("scal po review");
    expect(inventoryDispositionLabel("rewrite")).toBe("przepisz");
    expect(inventoryDispositionLabel("create")).toBe("utwórz");
  });
});
