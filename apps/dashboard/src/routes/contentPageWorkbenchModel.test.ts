import { describe, expect, it } from "vitest";

import { planningPageAssetsReady } from "./contentPageWorkbenchModel";

describe("planningPageAssetsReady", () => {
  it("requires every durable page asset before initial draft", () => {
    const complete = {
      title: "Tytuł",
      h1: "H1",
      lead: "Lead",
      meta_title: "Meta title",
      meta_description: "Meta description"
    };
    expect(planningPageAssetsReady(complete)).toBe(true);
    expect(planningPageAssetsReady({ ...complete, meta_description: " " })).toBe(false);
    expect(planningPageAssetsReady(null)).toBe(false);
  });
});
