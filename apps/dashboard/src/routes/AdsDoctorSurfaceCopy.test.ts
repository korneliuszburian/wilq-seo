import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("AdsDoctorSurface copy", () => {
  it("explains empty states as Ads decision limits", () => {
    const source = readFileSync("src/routes/AdsDoctorSurface.tsx", "utf8");
    expect(source).not.toContain('empty="brak');
    expect(source).toContain("nie oceniaj skuteczności z tego panelu");
    expect(source).toContain("nie traktuj tego jako rekomendacji Ads");
    expect(source).toContain("nie wykonuj zmiany bez review");
    expect(source).toContain("nie automatyzuj decyzji");
  });
});
