import { describe, expect, it } from "vitest";

import { formatContentMetricValue } from "./ContentDiagnosticSurface";

describe("formatContentMetricValue", () => {
  it("formats marketer-facing SEO metric values without raw float noise", () => {
    expect(formatContentMetricValue("ctr", 0.0445468509984639)).toBe("4,45%");
    expect(formatContentMetricValue("average_position", 1.6897081413210446)).toBe("1,69");
    expect(formatContentMetricValue("clicks", 123)).toBe("123");
    expect(formatContentMetricValue("impressions", 4429)).toBe("4429");
    expect(formatContentMetricValue("wordpress_match", true)).toBe("tak");
  });
});
