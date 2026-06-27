import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  contentBriefModeLabel,
  contentContractValueLabel,
  contentDraftGenerationStatusLabel,
  contentGateStatusLabel,
  contentWordPressPostStatusLabel,
  formatContentMetricValue
} from "../lib/contentLabels";

describe("formatContentMetricValue", () => {
  it("keeps content route contract wording sourced from API summaries", () => {
    const routeSource = readFileSync("src/routes/ContentDiagnosticSurface.tsx", "utf8");
    expect(routeSource).not.toContain("contentContractValueLabel");
  });

  it("formats marketer-facing SEO metric values without raw float noise", () => {
    expect(formatContentMetricValue("ctr", 0.0445468509984639)).toBe("4,45%");
    expect(formatContentMetricValue("average_position", 1.6897081413210446)).toBe("1,69");
    expect(formatContentMetricValue("clicks", 123)).toBe("123");
    expect(formatContentMetricValue("impressions", 4429)).toBe("4429");
    expect(formatContentMetricValue("wordpress_match", true)).toBe("tak");
  });

  it("keeps content domain labels in the shared registry instead of route-local copy", () => {
    expect(contentBriefModeLabel("refresh")).toBe("odświeżenie");
    expect(contentGateStatusLabel("confirmed_current_inventory")).toBe(
      "potwierdzone na obecnej stronie"
    );
    expect(contentDraftGenerationStatusLabel("blocked_until_content_review")).toBe(
      "zablokowany do kontroli treści i URL-a"
    );
  });

  it("hides internal contract version suffixes from content labels", () => {
    expect(contentContractValueLabel("content_draft_generation_v1")).toBe("generowanie szkicu");
    expect(contentContractValueLabel("content_url_preflight_review_v1")).toBe(
      "potwierdzenie publicznego URL-a"
    );
    expect(contentContractValueLabel("wordpress_draft_handoff_v1")).toBe(
      "zapis szkicu WordPress"
    );
    expect(contentContractValueLabel("wordpress_draft_handoff_preview_v1")).toBe(
      "podgląd szkicu WordPress"
    );
  });

  it("translates WordPress post status before it reaches marketer-facing cards", () => {
    expect(contentWordPressPostStatusLabel("draft")).toBe("szkic");
    expect(contentWordPressPostStatusLabel("publish")).toBe("opublikowany");
    expect(contentWordPressPostStatusLabel(null)).toBe("brak");
  });
});
