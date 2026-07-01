import { describe, expect, it } from "vitest";

import {
  adsCost,
  adsNumber,
  adsPercent,
  adsSignedCost,
  adsSignedNumber,
  adsStrategyContextValue,
  adsTargetStatusClass
} from "./adsFormatting";

describe("adsFormatting", () => {
  it("formats missing Ads values as decision limits", () => {
    expect(adsNumber(null)).toBe("wartość do potwierdzenia");
    expect(adsCost(undefined)).toBe("koszt do potwierdzenia");
    expect(adsPercent(null)).toBe("udział do potwierdzenia");
    expect(adsSignedNumber(undefined)).toBe("zmiana do potwierdzenia");
    expect(adsSignedCost(null)).toBe("zmiana kosztu do potwierdzenia");
    expect(adsStrategyContextValue("")).toBe("wartość do potwierdzenia");
  });

  it("formats numbers, costs, percentages and signed deltas consistently", () => {
    expect(adsNumber(1234.56789)).toBe(
      new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 4 }).format(1234.56789)
    );
    expect(adsCost(123_456_789, "PLN")).toBe(
      new Intl.NumberFormat("pl-PL", {
        currency: "PLN",
        maximumFractionDigits: 2,
        style: "currency"
      }).format(123.456789)
    );
    expect(adsCost(123_456_789)).toBe(
      `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
        123.456789
      )} jedn. konta`
    );
    expect(adsPercent(0.1234)).toBe("12,34%");
    expect(adsSignedNumber(2)).toBe("+2");
    expect(adsSignedNumber(-2)).toBe("-2");
    expect(adsSignedCost(1_000_000, "PLN")).toMatch(/^\+/);
    expect(adsSignedCost(-1_000_000, "PLN")).toMatch(/^-/);
    expect(adsStrategyContextValue(12.5)).toBe(adsNumber(12.5));
  });

  it("maps target statuses to stable visual classes", () => {
    expect(adsTargetStatusClass("spend_without_conversions")).toContain("text-amber-800");
    expect(adsTargetStatusClass("outside_target")).toContain("text-rose-800");
    expect(adsTargetStatusClass("within_target")).toContain("text-emerald-800");
    expect(adsTargetStatusClass("unknown")).toContain("text-slate-600");
  });
});
