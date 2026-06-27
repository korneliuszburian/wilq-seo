import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";

import { formatContentMetricValue } from "../lib/contentLabels";

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
    expect(routeSource).not.toContain("contentMetricFactLabel");
    expect(routeSource).not.toContain("contentConnectorStatusLabel");
    expect(routeSource).not.toContain("contentRefreshStatusLabel");
    expect(routeSource).not.toContain("contentBlockedClaimLabels");
    expect(routeSource).not.toContain("contentSectionLabel");
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
    expect(routeSource).toContain("connector.status_label");
    expect(routeSource).toContain("refresh.status_label");
    expect(routeSource).toContain("section.blocked_claim_labels");
    expect(routeSource).toContain("summary.blocked_claim_labels");
    expect(routeSource).toContain("fact.metric_label");
  });

  it("formats marketer-facing SEO metric values without raw float noise", () => {
    expect(formatContentMetricValue("ctr", 0.0445468509984639)).toBe("4,45%");
    expect(formatContentMetricValue("average_position", 1.6897081413210446)).toBe("1,69");
    expect(formatContentMetricValue("clicks", 123)).toBe("123");
    expect(formatContentMetricValue("impressions", 4429)).toBe("4429");
    expect(formatContentMetricValue("wordpress_match", true)).toBe("tak");
  });

  it("keeps removed content preview helpers out of the dashboard label registry", () => {
    const labelRegistry = readFileSync("src/lib/contentLabels.ts", "utf8");
    expect(labelRegistry).not.toContain("contentMetricFactLabel");
    expect(labelRegistry).not.toContain("contentContractValueLabel");
    expect(labelRegistry).not.toContain("contentGateStatusLabel");
    expect(labelRegistry).not.toContain("contentDecisionTypeLabel");
    expect(labelRegistry).not.toContain("contentAhrefsGapTypeLabel");
    expect(labelRegistry).not.toContain("contentAhrefsRelevanceLabel");
    expect(labelRegistry).not.toContain("contentAhrefsReasonLabel");
    expect(labelRegistry).not.toContain("contentConnectorStatusLabel");
    expect(labelRegistry).not.toContain("contentRefreshStatusLabel");
    expect(labelRegistry).not.toContain("contentBlockedClaimLabels");
    expect(labelRegistry).not.toContain("contentSectionLabel");
    expect(labelRegistry).not.toContain("contentBriefSourceLabel");
    expect(labelRegistry).not.toContain("contentBriefModeLabel");
    expect(labelRegistry).not.toContain("contentDraftOperationLabel");
    expect(labelRegistry).not.toContain("contentWordPressPostStatusLabel");
    expect(labelRegistry).not.toContain("contentDraftGenerationStatusLabel");
    expect(labelRegistry).not.toContain("contentPublicationReadinessLabel");
  });
});
