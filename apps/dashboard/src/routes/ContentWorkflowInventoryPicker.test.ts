import { describe, expect, it } from "vitest";

import { filterInventoryPageOptions } from "./ContentWorkflowSurface";

describe("filterInventoryPageOptions", () => {
  it("matches case-insensitively and caps the visible inventory", () => {
    const options = Array.from({ length: 35 }, (_, index) => ({
      workItemId: `item-${index}`,
      label: index === 12 ? "Baza wiedzy — /baza-wiedzy/" : `Strona ${index} — /strona-${index}/`
    }));

    expect(filterInventoryPageOptions(options, "BAZA WIEDZY")).toEqual([
      { workItemId: "item-12", label: "Baza wiedzy — /baza-wiedzy/" }
    ]);
    expect(filterInventoryPageOptions(options, "", 30)).toHaveLength(30);
  });
});
