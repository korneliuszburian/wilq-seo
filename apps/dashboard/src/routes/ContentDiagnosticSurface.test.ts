import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import {
  contentContractValueLabel,
  contentGateStatusLabel,
  formatContentMetricValue
} from "../lib/contentLabels";

describe("formatContentMetricValue", () => {
  it("keeps content route contract wording sourced from API summaries", () => {
    const routeSource = readFileSync("src/routes/ContentDiagnosticSurface.tsx", "utf8");
    expect(routeSource).not.toContain("contentContractValueLabel");
    expect(routeSource).not.toContain("contentDecisionTypeLabel");
    expect(routeSource).not.toContain("contentGateStatusLabel");
    expect(routeSource).not.toContain("wordpressMatchLabel");
    expect(routeSource).not.toContain("wordpressMatchConfidenceLabel");
    expect(routeSource).not.toContain("contentAhrefsGapTypeLabel");
    expect(routeSource).not.toContain("contentAhrefsRelevanceLabel");
    expect(routeSource).not.toContain("contentAhrefsReasonLabel");
    expect(routeSource).not.toContain("contentBriefSourceLabel");
    expect(routeSource).not.toContain("contentBriefModeLabel");
    expect(routeSource).not.toContain("contentDraftOperationLabel");
    expect(routeSource).not.toContain("contentWordPressPostStatusLabel");
    expect(routeSource).not.toContain("contentDraftGenerationStatusLabel");
    expect(routeSource).not.toContain("contentPublicationReadinessLabel");
    expect(routeSource).toContain("decision.decision_type_label");
    expect(routeSource).toContain("decision.inventory_gate_status_label");
    expect(routeSource).toContain("candidate.gap_type_label");
    expect(routeSource).toContain("candidate.business_relevance_reason_labels");
    expect(routeSource).toContain("preview.source_type_label");
    expect(routeSource).toContain("preview.mode_label");
    expect(routeSource).toContain("preview.operation_type_label");
    expect(routeSource).toContain("preview.post_status_label");
    expect(routeSource).toContain("preview.draft_generation_status_label");
    expect(routeSource).toContain("preview.publication_readiness_status_label");
  });

  it("formats marketer-facing SEO metric values without raw float noise", () => {
    expect(formatContentMetricValue("ctr", 0.0445468509984639)).toBe("4,45%");
    expect(formatContentMetricValue("average_position", 1.6897081413210446)).toBe("1,69");
    expect(formatContentMetricValue("clicks", 123)).toBe("123");
    expect(formatContentMetricValue("impressions", 4429)).toBe("4429");
    expect(formatContentMetricValue("wordpress_match", true)).toBe("tak");
  });

  it("keeps remaining content domain labels out of route-local copy", () => {
    expect(contentGateStatusLabel("confirmed_current_inventory")).toBe(
      "potwierdzone na obecnej stronie"
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

  it("keeps removed content preview helpers out of the dashboard label registry", () => {
    const labelRegistry = readFileSync("src/lib/contentLabels.ts", "utf8");
    expect(labelRegistry).not.toContain("contentBriefSourceLabel");
    expect(labelRegistry).not.toContain("contentBriefModeLabel");
    expect(labelRegistry).not.toContain("contentDraftOperationLabel");
    expect(labelRegistry).not.toContain("contentWordPressPostStatusLabel");
    expect(labelRegistry).not.toContain("contentDraftGenerationStatusLabel");
    expect(labelRegistry).not.toContain("contentPublicationReadinessLabel");
  });
});
