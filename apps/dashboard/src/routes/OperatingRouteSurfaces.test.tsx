import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("OperatingRouteSurfaces", () => {
  it("explains empty workflow outcomes instead of saying WILQ ma brak", () => {
    const source = readFileSync("src/routes/OperatingRouteSurfaces.tsx", "utf8");
    expect(source).not.toContain('WILQ ma {count || "brak"}');
    expect(source).not.toContain("WILQ ma brak");
    expect(source).toContain("Nie traktuj tego procesu jak gotowej decyzji");
  });
});
