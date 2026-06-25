import { describe, expect, it } from "vitest";

import {
  contentBriefModeLabel,
  contentDraftGenerationStatusLabel,
  contentTargetSiteMappingStatusLabel,
  contentTargetSiteStatusLabel,
  formatContentMetricValue
} from "../lib/contentLabels";

describe("formatContentMetricValue", () => {
  it("formats marketer-facing SEO metric values without raw float noise", () => {
    expect(formatContentMetricValue("ctr", 0.0445468509984639)).toBe("4,45%");
    expect(formatContentMetricValue("average_position", 1.6897081413210446)).toBe("1,69");
    expect(formatContentMetricValue("clicks", 123)).toBe("123");
    expect(formatContentMetricValue("impressions", 4429)).toBe("4429");
    expect(formatContentMetricValue("wordpress_match", true)).toBe("tak");
  });

  it("keeps content domain labels in the shared registry instead of route-local copy", () => {
    expect(contentBriefModeLabel("refresh")).toBe("odświeżenie");
    expect(contentTargetSiteStatusLabel("current_site_match")).toBe("bieżąca strona");
    expect(contentTargetSiteMappingStatusLabel("current_site_inventory_confirmed")).toBe(
      "potwierdzono obecną stronę"
    );
    expect(contentDraftGenerationStatusLabel("blocked_until_content_review")).toBe(
      "zablokowany do sprawdzenia treści"
    );
  });
});
