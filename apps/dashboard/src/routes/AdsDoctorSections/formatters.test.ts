import { describe, expect, it } from "vitest";

import { adsMissingDateLabel } from "../../lib/adsLabels";
import { dateLabel } from "./formatters";

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
