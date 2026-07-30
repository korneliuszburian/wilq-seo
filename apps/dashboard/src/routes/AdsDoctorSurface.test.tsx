import { readFileSync } from "node:fs";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getActions,
  getAdsDiagnosticsSummary,
  getDemandGenDiagnostics,
  getGa4Diagnostics
} from "../lib/api";
import { AdsDoctorSurface, readyGa4Diagnostics } from "./AdsDoctorSurface";

vi.mock("../lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../lib/api")>();
  return {
    ...actual,
    getActions: vi.fn(),
    getAdsDiagnosticsSummary: vi.fn(),
    getDemandGenDiagnostics: vi.fn(),
    getGa4Diagnostics: vi.fn()
  };
});

const observedAdsFact = {
  name: "campaign_count",
  metric_label: "Kampanie Ads",
  value: 2,
  period: "connector_refresh",
  period_label: "ostatni odczyt źródła",
  source_connector: "google_ads",
  source_connector_label: "Google Ads",
  evidence_id: "ev_ads_ready"
};

const adsReady = {
  generated_at: "2026-07-30T10:00:00Z",
  strict_instruction: "Wnioski o konwersjach wymagają gotowego GA4.",
  data_readiness: {
    state: "ready",
    state_label: "Ads gotowe",
    reason: "Ads mają potwierdzone fakty.",
    safe_next_step: "Przejrzyj Ads.",
    connector_id: "google_ads",
    connector_label: "Google Ads",
    evidence_ids: ["ev_ads_ready"],
    factual_metric_count: 1,
    factual_metrics: [observedAdsFact],
    coverage_label: "Potwierdzone Ads.",
    refresh_allowed: false
  },
  operator_summary: {
    action_summary_label: "bezpieczne sprawdzenie Ads",
    top_blocked_claim_labels: [],
    blocked_claim_labels: [],
    top_decision_ids: [],
    missing_read_contract_labels: [],
    campaign_count: 2,
    search_term_count: 3,
    total_cost_micros: 1000000,
    ready_area_count: 1,
    blocked_area_count: 0,
    operator_review_gate_summary_label: "review"
  },
  action_ids: [],
  decision_queue: [],
  evidence_summary_label: "1 dowód Ads",
  live_data_status_label: "metryki Ads dostępne",
  freshness_assessment: { state_label: "dane świeże", requires_refresh: false },
  account_currency_read_contract: { currency_code: "PLN" }
};

const ga4Blocked = {
  generated_at: "2026-07-30T10:00:00Z",
  data_readiness: {
    state: "blocked",
    state_label: "GA4 zablokowane",
    reason: "Dokładny powód GA4 z API.",
    safe_next_step: "Dokładny bezpieczny krok GA4 z API.",
    connector_id: "google_analytics_4",
    connector_label: "GA4",
    evidence_ids: [],
    factual_metric_count: 0,
    factual_metrics: [],
    coverage_label: "Brak potwierdzonych metryk GA4.",
    refresh_allowed: true
  },
  operator_summary: {
    measurement_issue_count: 999,
    blocked_claim_labels: ["Nie używaj sentinela GA4."],
    summary: "Sentinelowy opis GA4 nie może być widoczny.",
    next_step: "Sentinelowy krok GA4 nie może być widoczny."
  },
  decision_blocker_count: 999,
  conversion_readiness_contract: { status_label: "Sentinelowy status GA4", summary: "Sentinelowa konwersja." },
  freshness_assessment: { state_label: "Sentinelowa świeżość", requires_refresh: false },
  evidence_summary_label: "Sentinelowy dowód GA4",
  action_summary_label: "Sentinelowa akcja GA4"
};

describe("AdsDoctorSurface", () => {
  beforeEach(() => {
    vi.mocked(getAdsDiagnosticsSummary).mockReset();
    vi.mocked(getGa4Diagnostics).mockReset();
    vi.mocked(getActions).mockReset();
    vi.mocked(getDemandGenDiagnostics).mockReset();
    vi.mocked(getAdsDiagnosticsSummary).mockResolvedValue(adsReady as never);
    vi.mocked(getGa4Diagnostics).mockResolvedValue(ga4Blocked as never);
    vi.mocked(getActions).mockResolvedValue([]);
    vi.mocked(getDemandGenDiagnostics).mockResolvedValue(null as never);
  });

  it("does not promote a non-ready GA4 response into Ads measurement facts", () => {
    const blockedGa4 = {
      data_readiness: {
        state: "blocked"
      }
    };
    const readyGa4 = {
      data_readiness: {
        state: "ready"
      }
    };

    expect(readyGa4Diagnostics(blockedGa4)).toBeNull();
    expect(readyGa4Diagnostics(readyGa4)).toBe(readyGa4);
  });

  it("shows GA4's typed readiness instead of a zero or recommendation when Ads is ready", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <AdsDoctorSurface />
      </QueryClientProvider>
    );

    expect(await screen.findByText("Dokładny powód GA4 z API.")).toBeInTheDocument();
    expect(screen.getByText("Brak potwierdzonych metryk GA4.")).toBeInTheDocument();
    expect(screen.getByText("Dokładny bezpieczny krok GA4 z API.")).toBeInTheDocument();
    expect(screen.queryByText("999 problemy pomiaru")).not.toBeInTheDocument();
    expect(screen.queryByText("Sentinelowy opis GA4 nie może być widoczny.")).not.toBeInTheDocument();
    expect(screen.queryByText("Sentinelowy krok GA4 nie może być widoczny.")).not.toBeInTheDocument();
  });

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
    expect(routeSource).toContain("ga4Data.conversion_readiness_contract.status_label");
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
    expect(routeSource).toContain("readyGa4Diagnostics(ga4Response)");
    expect(routeSource).toContain("<DiagnosticDataReadinessPanel readiness={ga4Readiness} />");
    expect(routeSource).not.toContain("ga4Response?.operator_summary.measurement_issue_count ?? 0");
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
