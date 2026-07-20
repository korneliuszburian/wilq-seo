import { describe, expect, it } from "vitest";

import { hasReadableAcfSectionInventory } from "./ContentSectionWritingWorkbench";

describe("hasReadableAcfSectionInventory", () => {
  it("allows ACF preview only when the API exposes actual sections", () => {
    expect(
      hasReadableAcfSectionInventory({
        wordpress_acf_section_inventory_status: "available",
        wordpress_section_count: 3
      })
    ).toBe(true);
    expect(hasReadableAcfSectionInventory({ wordpress_section_count: 3 })).toBe(true);
  });

  it("does not invent ACF mapping for a page without readable sections", () => {
    expect(
      hasReadableAcfSectionInventory({
        wordpress_acf_section_inventory_status: "available",
        wordpress_section_count: 0
      })
    ).toBe(false);
    expect(
      hasReadableAcfSectionInventory({
        wordpress_acf_section_inventory_status: "missing",
        wordpress_section_count: null
      })
    ).toBe(false);
  });
});
