import { describe, expect, it } from "vitest";

import {
  inventoryDispositionLabel,
  planningReviewCheckedItems,
  planningSectionMapReady,
  planningScopeSummary,
  planningSourceSummary
} from "./ContentPlanningReviewPanel";

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

describe("planningSourceSummary", () => {
  it("shows source, material, knowledge and connector counts without raw IDs", () => {
    expect(
      planningSourceSummary({
        evidence_ids: ["ev_1", "ev_2"],
        source_material_ids: ["material_1"],
        knowledge_card_ids: ["card_1", "card_2"],
        source_connectors: ["gsc", "wordpress"]
      })
    ).toBe("Plan opiera się na 2 źródłach · 1 materiale Ekologusa · 2 kartach · 2 połączeniach");
  });
});

describe("planningReviewCheckedItems", () => {
  it("records explicit the_content provenance only after the marketer checks it", () => {
    expect(planningReviewCheckedItems("section_map", true, true, false)).toEqual([
      "kolejność, cel i źródła"
    ]);
    expect(planningReviewCheckedItems("section_map", true, true, true)).toEqual([
      "kolejność, cel i źródła",
      "existing_content_provenance"
    ]);
  });
});

describe("planningSectionMapReady", () => {
  it("treats only one generated proposal as a reviewable map", () => {
    const base = {
      generation_status: "baseline" as const,
      proposal_id: null
    };
    expect(planningSectionMapReady(base as never)).toBe(false);
    expect(
      planningSectionMapReady({
        ...base,
        generation_status: "codex_generated",
        proposal_id: "proposal_1"
      } as never)
    ).toBe(true);
  });
});
