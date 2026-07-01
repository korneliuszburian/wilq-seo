import { useState } from "react";

import { AdsDiagnosticsResponse } from "../lib/api";
import {
  AdsBudgetPacingRowsTable,
  AdsChangeHistoryRowsTable,
  AdsImpressionShareRowsTable,
  AdsRecommendationRowsPanel,
  AdsSharedBudgetDistributionPanel
} from "./AdsBudgetRecommendationPanels";
import {
  AdsBusinessTargetInterpretationPanel,
  AdsChangeImpactReadinessPanel
} from "./AdsBusinessReadinessPanels";
import {
  AdsCampaignRowsTable,
  AdsCampaignTriageRowsPanel,
  AdsDerivedKpiRowsTable
} from "./AdsCampaignPanels";
import {
  AdsCustomSegmentAudienceForecastPanel,
  AdsCustomSegmentCandidatesPanel
} from "./AdsCustomSegmentPanels";
import { AdsNegativeKeywordCandidatesPanel } from "./AdsNegativeKeywordCandidatesPanel";
import {
  AdsKeywordMatchContextRowsTable,
  AdsSearchTermNgramRowsTable,
  AdsSearchTermReviewSummaryPanel,
  AdsSearchTermRowsTable,
  AdsSearchTermSafetyRowsTable
} from "./AdsSearchTermPanels";
import { MetricTile } from "./OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "./TraceLine";

export function AdsMetricEvidencePanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode?: string;
}) {
  const [showDiagnosticTables, setShowDiagnosticTables] = useState(false);
  const summary = data.operator_summary;
  const campaignRows = data.campaign_read_contract.campaign_rows;
  const derivedKpiRows = data.derived_kpi_read_contract.kpi_rows;
  const budgetRows = data.budget_pacing_read_contract.budget_rows;
  const sharedBudgetRows =
    data.budget_pacing_read_contract.shared_budget_distribution_rows;
  const recommendationRows = data.recommendations_read_contract.recommendation_rows;
  const impressionShareRows = data.impression_share_read_contract.impression_share_rows;
  const campaignTriage = data.campaign_triage_read_contract;
  const campaignTriageRows = campaignTriage.triage_rows;
  const changeHistoryRows = data.change_history_read_contract.change_history_rows;
  const searchTermReview = data.search_term_review_summary_contract;
  const searchTermRows = data.search_terms_read_contract.search_term_rows;
  const searchTermNgramRows = data.search_term_ngram_read_contract.ngram_rows;
  const searchTermSafetyRows = data.search_term_safety_read_contract.safety_rows;
  const keywordContextRows = data.keyword_match_context_read_contract.context_rows;
  const customSegmentCandidates = data.custom_segments_read_contract.candidates;
  const customSegmentForecastRows =
    data.custom_segments_read_contract.audience_forecast_read_contract.forecast_rows;
  const negativeKeywordCandidates = data.negative_keywords_read_contract.candidates;
  const missingReadContractSummary = summary.missing_read_contract_summary_label;
  const operatorReviewGateSummary = summary.operator_review_gate_summary_label;
  const blockedClaimSummary = summary.blocked_claim_summary_label;

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki przeglądu Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót źródeł i blokad w WILQ. Decyzje dla marketera są powyżej;
            tutaj widać kampanie, zapytania i twierdzenia, których nie wolno używać.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
          <MetricTile label="Kampanie" value={campaignRows.length} />
          <MetricTile label="Wskaźniki" value={derivedKpiRows.length} />
          <MetricTile label="Budżety" value={budgetRows.length} />
          <MetricTile label="Wspólne budżety" value={sharedBudgetRows.length} />
          <MetricTile label="Rekomendacje" value={recommendationRows.length} />
          <MetricTile label="Udział" value={impressionShareRows.length} />
          <MetricTile label="Kolejka oceny" value={campaignTriageRows.length} />
          <MetricTile label="Zmiany" value={changeHistoryRows.length} />
          <MetricTile label="Ocena zapytań" value={searchTermReview.total_search_term_count} />
          <MetricTile label="Zapytania" value={searchTermRows.length} />
          <MetricTile label="N-gramy" value={searchTermNgramRows.length} />
          <MetricTile label="Bezpieczeństwo 90 dni" value={searchTermSafetyRows.length} />
          <MetricTile label="Słowa kluczowe" value={keywordContextRows.length} />
          <MetricTile label="Ocena wykl." value={negativeKeywordCandidates.length} />
          <MetricTile label="Segmenty" value={customSegmentCandidates.length} />
          <MetricTile label="Waluta" value={currencyCode ?? "waluta do potwierdzenia"} />
          <MetricTile
            label="Biznes"
            value={data.business_context_read_contract.status_label}
          />
        </div>
      </div>

      <div className="grid gap-4">
        <AdsBusinessTargetInterpretationPanel
          contract={data.business_context_read_contract}
        />
        <AdsCampaignTriageRowsPanel
          rows={campaignTriageRows}
          contract={campaignTriage}
          currencyCode={currencyCode}
        />
        <AdsChangeImpactReadinessPanel
          contract={data.change_impact_readiness_contract}
          currencyCode={currencyCode}
        />
        <AdsSearchTermReviewSummaryPanel
          contract={searchTermReview}
          currencyCode={currencyCode}
        />
        <AdsNegativeKeywordCandidatesPanel
          candidates={negativeKeywordCandidates}
          currencyCode={currencyCode}
        />
        <AdsCustomSegmentCandidatesPanel candidates={customSegmentCandidates} />
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={() => setShowDiagnosticTables((current) => !current)}
          className="rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
        >
          {showDiagnosticTables
            ? "Ukryj pełne tabele diagnostyczne"
            : "Pokaż pełne tabele diagnostyczne"}
        </button>
      </div>

      {showDiagnosticTables ? (
        <div className="mt-4 grid gap-4">
          <AdsCampaignRowsTable rows={campaignRows} currencyCode={currencyCode} />
          <AdsDerivedKpiRowsTable rows={derivedKpiRows} currencyCode={currencyCode} />
          <AdsBudgetPacingRowsTable
            rows={budgetRows}
            currencyCode={currencyCode}
            emptyStateMessage={data.budget_pacing_read_contract.empty_state_message}
          />
          <AdsSharedBudgetDistributionPanel
            rows={sharedBudgetRows}
            currencyCode={currencyCode}
          />
          <AdsRecommendationRowsPanel
            rows={recommendationRows}
            currencyCode={currencyCode}
          />
          <AdsImpressionShareRowsTable
            rows={impressionShareRows}
            emptyStateMessage={data.impression_share_read_contract.empty_state_message}
          />
          <AdsChangeHistoryRowsTable rows={changeHistoryRows} />
          <AdsSearchTermRowsTable rows={searchTermRows} currencyCode={currencyCode} />
          <AdsSearchTermNgramRowsTable
            rows={searchTermNgramRows}
            currencyCode={currencyCode}
          />
          <AdsSearchTermSafetyRowsTable
            rows={searchTermSafetyRows}
            currencyCode={currencyCode}
          />
          <AdsKeywordMatchContextRowsTable rows={keywordContextRows} />
          <AdsCustomSegmentAudienceForecastPanel rows={customSegmentForecastRows} />
        </div>
      ) : null}

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Brakujące dane" values={[missingReadContractSummary]} />
        <TraceLine
          label="Wymaga oceny"
          values={[operatorReviewGateSummary]}
          empty="WILQ nie podał wymaganej oceny; zostaje ręczny review."
        />
        <TraceLine label="Nie wolno twierdzić" values={[blockedClaimSummary]} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine
          label="Sekcje źródłowe"
          values={data.sections.map((section) => section.title)}
          empty="WILQ nie podał sekcji źródłowych; ten panel nie uzasadnia decyzji."
        />
      </div>
    </section>
  );
}
