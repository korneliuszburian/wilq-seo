import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("AdsDoctorSurface copy", () => {
  it("explains empty states as Ads decision limits", () => {
    const source = [
      readFileSync("src/routes/AdsDoctorSurface.tsx", "utf8"),
      readFileSync("src/components/AdsOperatorSummaryPanels.tsx", "utf8"),
      readFileSync("src/components/AdsBudgetRecommendationPanels.tsx", "utf8"),
      readFileSync("src/components/AdsBusinessReadinessPanels.tsx", "utf8"),
      readFileSync("src/lib/adsLabels.ts", "utf8")
    ].join("\n");
    expect(source).not.toContain('empty="brak');
    expect(source).toContain("nie oceniaj skuteczności z tego panelu");
    expect(source).toContain("nie traktuj tego jako rekomendacji Ads");
    expect(source).toContain("nie wykonuj zmiany bez review");
    expect(source).toContain("nie automatyzuj decyzji");
    expect(source).toContain("bez ostatniego odczytu; nie oceniaj trendu");
    expect(source).toContain("nie ma podglądu zmian; nie zapisuj zmiany");
    expect(source).toContain("metryki kampanii niepotwierdzone; nie oceniaj wpływu");
  });
});
