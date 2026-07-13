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
    const campaignPanelsSource = readFileSync(
      "src/components/AdsCampaignPanels.tsx",
      "utf8"
    );
    const operatorSummaryPanelsSource = readFileSync(
      "src/components/AdsOperatorSummaryPanels.tsx",
      "utf8"
    );
    const metricEvidencePanelSource = readFileSync(
      "src/components/AdsMetricEvidencePanel.tsx",
      "utf8"
    );
    const overviewPanelsSource = readFileSync(
      "src/components/AdsOverviewPanels.tsx",
      "utf8"
    );
    const budgetRecommendationPanelsSource = readFileSync(
      "src/components/AdsBudgetRecommendationPanels.tsx",
      "utf8"
    );
    const businessReadinessPanelsSource = readFileSync(
      "src/components/AdsBusinessReadinessPanels.tsx",
      "utf8"
    );
    const negativeKeywordPanelSource = readFileSync(
      "src/components/AdsNegativeKeywordCandidatesPanel.tsx",
      "utf8"
    );
    const searchTermPanelsSource = readFileSync(
      "src/components/AdsSearchTermPanels.tsx",
      "utf8"
    );
    const traceLineSource = readFileSync("src/components/TraceLine.tsx", "utf8");
    expect(routeSource).not.toContain('empty="brak"');
    expect(traceLineSource).not.toContain('empty = "brak"');
    expect(routeSource).toContain("data.evidence_summary_label");
    expect(routeSource).toContain("data.action_summary_label");
    expect(routeSource).toContain("summary.action_summary_label");
    expect(routeSource).toContain("getGa4Diagnostics");
    expect(routeSource).toContain("getDemandGenDiagnostics");
    expect(routeSource).toContain("ForbiddenClaimsStrip");
    expect(overviewPanelsSource).toContain("primaryDecision?.action_summary_label");
    expect(overviewPanelsSource).toContain("summary.missing_read_contract_summary_label");
    expect(overviewPanelsSource).toContain("summary.blocked_claim_summary_label");
    expect(operatorSummaryPanelsSource).toContain("optimizer_readiness_contract");
    expect(operatorSummaryPanelsSource).toContain("contract.mode_label");
    expect(operatorSummaryPanelsSource).toContain("item.missing_read_contract_summary_label");
    expect(operatorSummaryPanelsSource).toContain("item.source_contract_summary_label");
    expect(businessReadinessPanelsSource).toContain("interpretation.allowed_use_labels");
    expect(businessReadinessPanelsSource).toContain("interpretation.blocked_use_labels");
    expect(businessReadinessPanelsSource).toContain("interpretation.missing_requirement_labels");
    expect(businessReadinessPanelsSource).toContain("interpretation.status_label");
    expect(businessReadinessPanelsSource).toContain("interpretation.policy_summary_label");
    expect(businessReadinessPanelsSource).toContain("interpretation.action_summary_label");
    expect(businessReadinessPanelsSource).toContain("strategyReadiness.status_label");
    expect(businessReadinessPanelsSource).toContain("strategyReadiness.latest_review_status_label");
    expect(businessReadinessPanelsSource).toContain(
      "strategyReadiness.required_validation_summary_label"
    );
    expect(businessReadinessPanelsSource).toContain(
      "strategyReadiness.missing_read_contract_summary_label"
    );
    expect(businessReadinessPanelsSource).toContain("strategyReadiness.blocked_claim_summary_label");
    expect(businessReadinessPanelsSource).toContain("strategyReadiness.action_summary_label");
    expect(operatorSummaryPanelsSource).toContain("decision.start_here_summary");
    expect(operatorSummaryPanelsSource).toContain("decision.action_summary_label");
    expect(operatorSummaryPanelsSource).toContain("decision.blocked_claim_summary_label");
    expect(overviewPanelsSource).toContain("primaryDecision?.measurement_plan");
    expect(overviewPanelsSource).toContain("summary.missing_read_contract_summary_label");
    expect(metricEvidencePanelSource).toContain("summary.operator_review_gate_summary_label");
    expect(overviewPanelsSource).toContain("summary.blocked_claim_summary_label");
    expect(overviewPanelsSource).toContain("summary.top_blocked_claim_labels");
    expect(overviewPanelsSource).toContain("summary.top_blocked_claim_summary_label");
    expect(overviewPanelsSource).toContain("primaryDecision.missing_read_contract_summary_label");
    expect(metricEvidencePanelSource).toContain("business_context_read_contract.status_label");
    expect(campaignPanelsSource).toContain("row.advertising_channel_type_label");
    expect(campaignPanelsSource).toContain("row.campaign_status_label");
    expect(budgetRecommendationPanelsSource).toContain("row.budget_period_label");
    expect(budgetRecommendationPanelsSource).toContain("row.blocked_claim_summary_label");
    expect(budgetRecommendationPanelsSource).toContain("row.human_review_gate_summary_label");
    expect(budgetRecommendationPanelsSource).toContain("row.changed_field_summary_label");
    expect(operatorSummaryPanelsSource).not.toContain(
      "{decision.decision_type_label} / {decision.status_label}"
    );
    expect(operatorSummaryPanelsSource).not.toContain("{item.status_label} / {item.risk_label}");
    expect(businessReadinessPanelsSource).not.toContain(
      "{strategyReadiness.status_label} / {strategyReadiness.latest_review_status_label}"
    );
    expect(routeSource).not.toContain("{row.review_priority} / {row.review_score}");
    expect(routeSource).not.toContain("{row.review_priority} / wynik {row.review_score}");
    expect(campaignPanelsSource).toContain("adsMissingChannelLabel");
    expect(campaignPanelsSource).toContain("adsMissingCampaignStatusLabel");
    expect(routeSource).not.toContain("{row.advertising_channel_type_label} / {row.budget_period_label}");
    expect(routeSource).not.toContain(
      "{share.advertising_channel_type_label} / {share.campaign_status_label}"
    );
    expect(routeSource).not.toContain("} / koszt{\" \"}");
    expect(negativeKeywordPanelSource).not.toContain(
      "{candidate.review_priority} / {candidate.review_score}"
    );
    expect(routeSource).not.toContain("{row.keyword_text} / {row.match_type_label}");
    expect(searchTermPanelsSource).not.toContain("{row.keyword_text} / {row.match_type_label}");
    expect(routeSource).not.toContain("row.blocked_claim_labels.slice(0, 2).join");
    expect(routeSource).not.toContain("row.human_review_gate_labels.slice(0, 2).join");
    expect(routeSource).not.toContain("row.changed_field_labels.slice(0, 4).join");
    expect(operatorSummaryPanelsSource).not.toContain(
      "summary.blocked_claim_labels.slice(0, 8)"
    );
    expect(operatorSummaryPanelsSource).not.toContain(
      "decision.blocked_claim_labels.slice(0, 3)"
    );
    expect(overviewPanelsSource).not.toContain("primaryDecision.blocked_claim_labels");
    expect(routeSource).not.toContain("row.payload_preview.operation_type_label");
    expect(budgetRecommendationPanelsSource).toContain("row.recommendation_type_label");
    expect(budgetRecommendationPanelsSource).toContain("row.preview_card");
    expect(routeSource).not.toContain("Operacja: {row.payload_preview.operation_type_label}");
    expect(routeSource).not.toContain("Wspólne budget_id");
    expect(routeSource).not.toContain("ID budżetu:");
    expect(negativeKeywordPanelSource).toContain("candidate.preview_card");
    expect(negativeKeywordPanelSource).not.toContain("candidate.payload_preview");
    expect(searchTermPanelsSource).toContain("contract.operator_review_gate_summary_label");
    expect(searchTermPanelsSource).toContain("contract.blocked_claim_summary_label");
    expect(businessReadinessPanelsSource).toContain("row.missing_read_contract_summary_label");
    expect(budgetRecommendationPanelsSource).toContain("row.human_review_gate_summary_label");
    expect(routeSource).not.toContain("adsCampaignTriageNextStep");
    expect(routeSource).not.toContain("row.missing_read_contract_labels");
    expect(routeSource).not.toContain("row.blocked_claim_labels");
    expect(routeSource).not.toContain("row.human_review_gate_labels.slice(0, 3)");
    expect(operatorSummaryPanelsSource).not.toContain("adsOptimizerReadinessTitle");
    expect(operatorSummaryPanelsSource).not.toContain("adsOptimizerReadinessSummary");
    expect(operatorSummaryPanelsSource).not.toContain("adsOptimizerReadinessNextStep");
    expect(operatorSummaryPanelsSource).not.toContain("adsOptimizerReadinessItemLabel");
    expect(operatorSummaryPanelsSource).not.toContain("adsOptimizerModeLabel");
    expect(routeSource).not.toContain("adsBusinessUseLabel");
    expect(routeSource).not.toContain("adsStrategyReviewStatusLabel");
    expect(operatorSummaryPanelsSource).not.toContain("adsStartHereSummary");
    expect(routeSource).not.toContain("adsCondensedMeasurementPlan");
    expect(routeSource).not.toContain("adsBusinessContextStatusValue");
    expect(routeSource).not.toContain("adsCampaignReviewReason");
    expect(routeSource).not.toContain("adsCampaignTriageReason");
    expect(routeSource).not.toContain("adsRecommendationReviewReason");
    expect(operatorSummaryPanelsSource).not.toContain("adsDecisionStatusLabel");
    expect(operatorSummaryPanelsSource).not.toContain("adsRiskLabel");
    expect(routeSource).not.toContain("connectorLabelsFromStatuses");
    expect(businessReadinessPanelsSource).not.toContain("interpretation.interpretation_contract");
    expect(businessReadinessPanelsSource).not.toContain("interpretation.status}");
    expect(routeSource).not.toContain(
      "summary.missing_read_contracts.map(adsMissingReadContractLabel)"
    );
    expect(businessReadinessPanelsSource).not.toContain(
      "interpretation.missing_requirements.map(adsMissingReadContractLabel)"
    );
    expect(businessReadinessPanelsSource).not.toContain(
      "strategyReadiness.missing_read_contracts.map(adsMissingReadContractLabel)"
    );
    expect(businessReadinessPanelsSource).not.toContain(
      "strategyReadiness.blocked_claims.map(adsBlockedClaimLabel)"
    );
    expect(operatorSummaryPanelsSource).not.toContain(
      "summary.blocked_claims.map(adsBlockedClaimLabel)"
    );
    expect(routeSource).not.toContain("data.evidence_ids.length");
    expect(routeSource).not.toContain("formatActionObjectCount(actions.length)");
    expect(routeSource).not.toContain("formatActionObjectCount");
    expect(operatorSummaryPanelsSource).not.toContain("summary.action_ids.length");
    expect(operatorSummaryPanelsSource).not.toContain("decision.action_ids.length");
    expect(businessReadinessPanelsSource).not.toContain("interpretation.action_ids.length");
    expect(businessReadinessPanelsSource).not.toContain("strategyReadiness.action_ids.length");
    expect(routeSource).not.toContain("row.action_ids.length");
    expect(businessReadinessPanelsSource).toContain(
      "strategyReadiness.missing_read_contract_summary_label"
    );
    expect(routeSource).not.toContain("formatAdsEvidenceCount");
    expect(routeSource).not.toContain("formatTraceIdCount");
    expect(routeSource).not.toContain("formatAdsContractCount");
    expect(operatorSummaryPanelsSource).not.toContain("item.source_contract_ids.length");
    expect(businessReadinessPanelsSource).not.toContain("interpretation.policy_ids.length");
    expect(businessReadinessPanelsSource).not.toContain(
      "strategyReadiness.required_validation.length"
    );
    expect(businessReadinessPanelsSource).not.toContain(
      "strategyReadiness.missing_read_contracts.length"
    );
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
