import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

describe("AdsDoctorSurface", () => {
  it("ads doctor route renders live metric-backed diagnostics", () => {
    const routeSource = readFileSync("src/routes/AdsDoctorSurface.tsx", "utf8");
    expect(routeSource).toContain('title="Reklamy i pomiar"');
    expect(routeSource).toContain("Najpierw pomiar");
    expect(routeSource).toContain("Kolejka diagnostyczna");
    expect(routeSource).toContain("Bezpieczne tryby pracy");
    expect(routeSource).toContain("ForbiddenClaimsStrip");
    expect(routeSource).toContain("ROAS, przychód, waste i konwersje są zablokowane");
    expect(routeSource).toContain("Review Ads");
    expect(routeSource).toContain("Sprawdź pomiar GA4");
    expect(routeSource).toContain("Demand Gen tylko do gotowości");
    expect(routeSource).toContain("ActionObject");
    expect(routeSource).toContain('href="/actions"');
    expect(routeSource).not.toContain('href="/ads-doctor/search-terms"');
    expect(routeSource).toContain("summary.total_cost_micros");
    expect(routeSource).toContain("summary.campaign_count");
    expect(routeSource).toContain("summary.search_term_count");
    expect(routeSource).toContain("ga4Data?.conversion_readiness_contract.status_label");
    expect(routeSource).toContain("demandGenData?.summary");
    expect(routeSource).not.toContain("werdykt przepalonego budżetu");
    const traceLineSource = readFileSync("src/components/TraceLine.tsx", "utf8");
    expect(routeSource).not.toContain('empty="brak"');
    expect(traceLineSource).not.toContain('empty = "brak"');
    expect(routeSource).toContain("data.evidence_summary_label");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("summary.action_summary_label");
    expect(routeSource).toContain("getGa4Diagnostics");
    expect(routeSource).toContain("getDemandGenDiagnostics");
    expect(routeSource).toContain("ForbiddenClaimsStrip");
    expect(routeSource).not.toContain("{row.review_priority} / {row.review_score}");
    expect(routeSource).not.toContain("{row.review_priority} / wynik {row.review_score}");
    expect(routeSource).not.toContain("{row.advertising_channel_type_label} / {row.budget_period_label}");
    expect(routeSource).not.toContain(
      "{share.advertising_channel_type_label} / {share.campaign_status_label}"
    );
    expect(routeSource).not.toContain("} / koszt{\" \"}");
    expect(routeSource).not.toContain("{row.keyword_text} / {row.match_type_label}");
    expect(routeSource).not.toContain("row.blocked_claim_labels.slice(0, 2).join");
    expect(routeSource).not.toContain("row.human_review_gate_labels.slice(0, 2).join");
    expect(routeSource).not.toContain("row.changed_field_labels.slice(0, 4).join");
    expect(routeSource).not.toContain("row.payload_preview.operation_type_label");
    expect(routeSource).not.toContain("Operacja: {row.payload_preview.operation_type_label}");
    expect(routeSource).not.toContain("Wspólne budget_id");
    expect(routeSource).not.toContain("ID budżetu:");
    expect(routeSource).not.toContain("adsCampaignTriageNextStep");
    expect(routeSource).not.toContain("row.missing_read_contract_labels");
    expect(routeSource).not.toContain("row.blocked_claim_labels");
    expect(routeSource).not.toContain("row.human_review_gate_labels.slice(0, 3)");
    expect(routeSource).not.toContain("adsBusinessUseLabel");
    expect(routeSource).not.toContain("adsStrategyReviewStatusLabel");
    expect(routeSource).not.toContain("adsCondensedMeasurementPlan");
    expect(routeSource).not.toContain("adsBusinessContextStatusValue");
    expect(routeSource).not.toContain("adsCampaignReviewReason");
    expect(routeSource).not.toContain("adsCampaignTriageReason");
    expect(routeSource).not.toContain("adsRecommendationReviewReason");
    expect(routeSource).not.toContain("connectorLabelsFromStatuses");
    expect(routeSource).not.toContain(
      "summary.missing_read_contracts.map(adsMissingReadContractLabel)"
    );
    expect(routeSource).not.toContain("data.evidence_ids.length");
    expect(routeSource).not.toContain("formatActionObjectCount(actions.length)");
    expect(routeSource).not.toContain("formatActionObjectCount");
    expect(routeSource).not.toContain("row.action_ids.length");
    expect(routeSource).not.toContain("formatAdsEvidenceCount");
    expect(routeSource).not.toContain("formatTraceIdCount");
    expect(routeSource).not.toContain("formatAdsContractCount");
    expect(readFileSync("src/routes/OperatingRouteSurfaces.tsx", "utf8")).not.toContain(
      "formatEvidenceCount(action.evidence_ids.length)"
    );
    expect(readFileSync("src/routes/RegistryPanels.tsx", "utf8")).not.toContain(
      "formatEvidenceCount(action.evidence_ids.length)"
    );
    expect(readFileSync("src/routes/RegistryPanels.tsx", "utf8")).not.toContain(
      "formatEvidenceCount(run.evidence_ids.length)"
    );
  });

});
