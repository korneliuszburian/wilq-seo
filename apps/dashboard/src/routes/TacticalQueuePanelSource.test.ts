import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("TacticalQueuePanel source copy", () => {
  it("explains empty evidence and action states as decision limits", () => {
    const source = readFileSync("src/routes/TacticalQueuePanel.tsx", "utf8");
    expect(source).not.toContain('empty="brak dowodów do pokazania"');
    expect(source).not.toContain('empty="brak akcji do sprawdzenia"');
    expect(source).toContain("nie traktuj tej pozycji jako rekomendacji");
    expect(source).toContain("następny krok musi pozostać ręczną oceną");
  });
});
