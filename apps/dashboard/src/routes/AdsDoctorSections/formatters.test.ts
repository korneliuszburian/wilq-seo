import { describe, expect, it } from "vitest";

import { adsMissingDateLabel } from "../../lib/adsLabels";
import { adsPriorityLabel, adsRisk, adsRiskLabel, dateLabel } from "./formatters";

type AdsDecisionInput = Parameters<typeof adsRisk>[0];

function adsDecision(overrides: Partial<AdsDecisionInput>): AdsDecisionInput {
  return {
    status: "ready",
    priority_label: "",
    status_label: "",
    risk: "low",
    risk_label: "",
    ...overrides
  } as AdsDecisionInput;
}

describe("dateLabel", () => {
  it.each([
    [null, adsMissingDateLabel],
    ["", adsMissingDateLabel],
    ["not-a-date", adsMissingDateLabel]
  ])("labels %j as unconfirmed when the date is not valid", (value, expected) => {
    expect(dateLabel(value)).toBe(expected);
  });

  it("keeps the established Polish date format for a valid timestamp", () => {
    expect(dateLabel("2025-05-15T12:00:00.000Z")).toBe("15 maja 2025");
  });
});

describe("adsRisk", () => {
  it("preserves the critical risk tier instead of degrading it", () => {
    expect(adsRisk(adsDecision({ risk: "critical" }))).toBe("critical");
  });

  it("maps a blocked status to the blocked risk tier", () => {
    expect(adsRisk(adsDecision({ status: "blocked", risk: "low" }))).toBe("blocked");
  });
});

describe("adsPriorityLabel", () => {
  it("uses the API-owned priority label", () => {
    expect(adsPriorityLabel(adsDecision({ priority_label: "najpierw" }))).toBe("najpierw");
  });

  it("falls back to a Polish placeholder when the API label is missing", () => {
    expect(adsPriorityLabel(adsDecision({ priority_label: "  " }))).toBe("brak priorytetu");
  });
});

describe("adsRiskLabel", () => {
  it("prefers the API risk label", () => {
    expect(
      adsRiskLabel(adsDecision({ risk_label: "krytyczne", status_label: "blokada" }))
    ).toBe("krytyczne");
  });

  it("never falls back to a raw status enum", () => {
    expect(adsRiskLabel(adsDecision({ risk_label: "", status_label: "" }))).toBe(
      "status do sprawdzenia"
    );
  });
});
