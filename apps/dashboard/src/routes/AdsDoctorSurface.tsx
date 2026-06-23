import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { AdsDiagnosticsResponse, getActions, getAdsDiagnostics } from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { ActionObjectFocus } from "./ActionObjectPanels";
import {
  AdsCustomSegmentAudienceForecastPanel,
  AdsCustomSegmentCandidatesPanel
} from "./CustomSegmentsDiagnosticSurface";
import {
  adsBlockedClaimLabel,
  adsMissingReadContractLabel
} from "./marketingLabels";

type AdsBlockedHandoff = NonNullable<AdsDiagnosticsResponse["blocked_handoff"]>;
type AdsDecisionItem = AdsDiagnosticsResponse["decision_queue"][number];
type AdsCampaignMetricRow = AdsDiagnosticsResponse["campaign_read_contract"]["campaign_rows"][number];
type AdsDerivedKpiRow = AdsDiagnosticsResponse["derived_kpi_read_contract"]["kpi_rows"][number];
type AdsBudgetPacingRow =
  AdsDiagnosticsResponse["budget_pacing_read_contract"]["budget_rows"][number];
type AdsSharedBudgetDistributionRow =
  AdsDiagnosticsResponse["budget_pacing_read_contract"]["shared_budget_distribution_rows"][number];
type AdsRecommendationRow =
  AdsDiagnosticsResponse["recommendations_read_contract"]["recommendation_rows"][number];
type AdsImpressionShareRow =
  AdsDiagnosticsResponse["impression_share_read_contract"]["impression_share_rows"][number];
type AdsCampaignTriageRow =
  AdsDiagnosticsResponse["campaign_triage_read_contract"]["triage_rows"][number];
type AdsOptimizerReadinessItem =
  AdsDiagnosticsResponse["optimizer_readiness_contract"]["readiness_items"][number];
type AdsChangeHistoryRow =
  AdsDiagnosticsResponse["change_history_read_contract"]["change_history_rows"][number];
type AdsChangeImpactReadinessRow =
  AdsDiagnosticsResponse["change_impact_readiness_contract"]["readiness_rows"][number];
type AdsSearchTermMetricRow =
  AdsDiagnosticsResponse["search_terms_read_contract"]["search_term_rows"][number];
type AdsSearchTermNgramRow =
  AdsDiagnosticsResponse["search_term_ngram_read_contract"]["ngram_rows"][number];
type AdsSearchTermSafetyRow =
  AdsDiagnosticsResponse["search_term_safety_read_contract"]["safety_rows"][number];
type AdsKeywordMatchContextRow =
  AdsDiagnosticsResponse["keyword_match_context_read_contract"]["context_rows"][number];
type AdsNegativeKeywordCandidate =
  AdsDiagnosticsResponse["negative_keywords_read_contract"]["candidates"][number];

export function AdsDoctorSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics"],
    queryFn: getAdsDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ads/diagnostics. Ads Doctor nie może udawać diagnozy bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. Ads Doctor nie może pokazać walidacji ani podglądu akcji." />
      </main>
    );
  }

  const data = diagnostics.data;
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;
  const blockedDecisionCount = data.decision_queue.filter(
    (decision) => decision.status === "blocked"
  ).length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Ads Doctor</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Google Ads z WILQ API. Pokazuje, co marketer może
            uczciwie sprawdzić na podstawie kampanii i zapytań oraz które claimy
            pozostają zablokowane bez kolejnych kontraktów odczytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Blockery" value={blockedDecisionCount} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
          <MetricTile label="Waluta" value={currencyCode ?? "brak"} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Google Ads
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.id}: {adsConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki Ads dostępne" : "brak metryk Ads"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {adsRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      {data.blocked_handoff ? <AdsBlockedHandoffPanel handoff={data.blocked_handoff} /> : null}

      <AdsMarketSnapshot data={data} currencyCode={currencyCode} />
      <AdsOperatorSummary data={data} />

      <AdsMetricEvidencePanel data={data} currencyCode={currencyCode} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

    </main>
  );
}

function AdsMarketSnapshot({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
}) {
  const summary = data.operator_summary;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Aktualny odczyt Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Szybki obraz tego, co WILQ może dziś uczciwie przejrzeć w Ads.
            Apply, waste, CPA/ROAS verdict i skalowanie budżetu pozostają
            zablokowane do czasu walidacji ActionObject i brakujących kontraktów.
          </p>
        </div>
        <MetricTile label="Waluta" value={currencyCode ?? "brak"} />
      </div>
      <div className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-600">
        Wartości Ads
      </div>
      <div className="grid gap-2 text-center text-xs sm:grid-cols-2 xl:grid-cols-5">
        <MetricTile label="Kliknięcia" value={adsNumber(summary.total_clicks)} />
        <MetricTile label="Wyświetlenia" value={adsNumber(summary.total_impressions)} />
        <MetricTile label="Koszt" value={adsCost(summary.total_cost_micros, currencyCode)} />
        <MetricTile label="Konwersje" value={adsNumber(summary.total_conversions)} />
        <MetricTile label="Wartość konw." value={adsNumber(summary.total_conversion_value)} />
      </div>
      <div className="mt-3 grid gap-2 text-center text-xs sm:grid-cols-3 xl:grid-cols-6">
        <MetricTile label="Kampanie" value={summary.campaign_count} />
        <MetricTile label="Zapytania" value={summary.search_term_count} />
        <MetricTile
          label="Rekom."
          value={data.recommendations_read_contract.recommendation_rows.length}
        />
        <MetricTile label="Budżety" value={data.budget_pacing_read_contract.budget_rows.length} />
        <MetricTile label="Ready" value={summary.ready_area_count} />
        <MetricTile label="Blocked" value={summary.blocked_area_count} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Brakujące kontrakty"
          values={summary.missing_read_contracts.map(adsMissingReadContractLabel)}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={summary.blocked_claims.map(adsBlockedClaimLabel).slice(0, 8)}
          empty="brak"
        />
      </div>
    </section>
  );
}

function AdsOperatorSummary({ data }: { data: AdsDiagnosticsResponse }) {
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const optimizer = data.optimizer_readiness_contract;
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const decisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is AdsDecisionItem => Boolean(decision));
  const allowedMetrics = summary.allowed_metrics.map(adsAllowedMetricLabel);
  const missingReadContracts = summary.missing_read_contracts.map(adsMissingReadContractLabel);
  const operatorReviewGates = summary.operator_review_gates.map(adsOperatorReviewGateLabel);
  const blockedClaims = summary.blocked_claims.map(adsBlockedClaimLabel);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{summary.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{summary.summary}</p>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-ink">
            {summary.next_step}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Kampanie" value={summary.campaign_count} />
          <MetricTile label="Budżety" value={data.budget_pacing_read_contract.budget_rows.length} />
          <MetricTile
            label="Rekom."
            value={data.recommendations_read_contract.recommendation_rows.length}
          />
          <MetricTile
            label="Udział"
            value={data.impression_share_read_contract.impression_share_rows.length}
          />
          <MetricTile
            label="Zmiany"
            value={data.change_history_read_contract.change_history_rows.length}
          />
          <MetricTile
            label="Zapytania"
            value={summary.search_term_count}
          />
          <MetricTile label="Ready" value={summary.ready_area_count} />
          <MetricTile label="Blocked" value={summary.blocked_area_count} />
        </div>
      </div>

      <AdsOptimizerReadinessPanel contract={optimizer} />

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {decisions.length > 0 ? (
            decisions.map((decision) => (
              <AdsDecisionCard
                key={decision.id}
                decision={decision}
                currencyCode={currencyCode}
              />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji Ads. Najpierw uruchom odczyt Google Ads." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb Ads</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine label="Metryki dostępne" values={allowedMetrics} empty="brak" />
            <TraceLine
              label="Waluta konta"
              values={[data.account_currency_read_contract.currency_code ?? "brak"]}
              empty="brak"
            />
            <TraceLine label="Brakujące kontrakty" values={missingReadContracts} empty="brak" />
            <TraceLine label="Wymagany review" values={operatorReviewGates} empty="brak" />
            <LinkedTraceLine label="Dowody" values={summary.evidence_ids.slice(0, 6)} kind="evidence" />
            <LinkedTraceLine label="ActionObjecty" values={summary.action_ids} kind="actions" />
            <TraceLine label="Nie wolno twierdzić" values={blockedClaims} empty="brak" />
          </div>
        </div>
      </div>
    </section>
  );
}

function AdsOptimizerReadinessPanel({
  contract
}: {
  contract: AdsDiagnosticsResponse["optimizer_readiness_contract"];
}) {
  const readyItems = contract.readiness_items.filter((item) => item.status === "ready");
  const blockedItems = contract.readiness_items.filter((item) => item.status === "blocked");

  return (
    <div className="mb-4 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">
            Co można zrobić teraz w Ads
          </h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            {contract.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Gotowe" value={contract.ready_area_count} />
          <MetricTile label="Zablokowane" value={contract.blocked_area_count} />
          <MetricTile label="Tryb" value={contract.mode} />
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <AdsOptimizerReadinessGroup
          title="Gotowe do review"
          items={readyItems}
          empty="Brak obszarów gotowych do review."
        />
        <AdsOptimizerReadinessGroup
          title="Zablokowane claimy / apply"
          items={blockedItems}
          empty="Brak aktywnych blockerów."
        />
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Brakujące kontrakty"
          values={contract.missing_read_contracts.map(adsMissingReadContractLabel)}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={contract.blocked_claims.map(adsBlockedClaimLabel)}
          empty="brak"
        />
        <LinkedTraceLine
          label="Dowody"
          values={contract.evidence_ids.slice(0, 6)}
          kind="evidence"
          empty="brak"
        />
        <LinkedTraceLine
          label="ActionObjecty"
          values={contract.action_ids}
          kind="actions"
          empty="brak"
        />
      </div>
    </div>
  );
}

function AdsOptimizerReadinessGroup({
  title,
  items,
  empty
}: {
  title: string;
  items: AdsOptimizerReadinessItem[];
  empty: string;
}) {
  if (items.length === 0) {
    return <BlockerNotice message={empty} />;
  }

  return (
    <div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-normal text-slate-500">
        {title}
      </div>
      <div className="grid gap-2">
        {items.slice(0, 5).map((item) => (
          <article key={item.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">
                  {adsOptimizerReadinessItemLabel(item.id)}
                </h4>
                <p className="mt-1 text-xs text-slate-500">{item.title}</p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {adsDecisionStatusLabel(item.status)} / {adsRiskLabel(item.risk)}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">{item.summary}</p>
            <p className="mt-2 text-xs font-medium text-ink">{item.next_step}</p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Kontrakty"
                values={item.source_contract_ids}
                empty="brak"
              />
              <TraceLine
                label="Braki"
                values={item.missing_read_contracts.map(adsMissingReadContractLabel)}
                empty="brak"
              />
              <TraceLine
                label="Blokady"
                values={item.blocked_claims.map(adsBlockedClaimLabel)}
                empty="brak"
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsDecisionCard({
  decision,
  currencyCode
}: {
  decision: AdsDecisionItem;
  currencyCode?: string;
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {adsDecisionTypeLabel(decision.decision_type)} / {adsDecisionStatusLabel(decision.status)}
          </p>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          ryzyko: {adsRiskLabel(decision.risk)}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{decision.rationale}</p>
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-700 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      {decision.negative_keyword_candidates.length > 0 ? (
        <AdsNegativeKeywordCandidatesPanel
          candidates={decision.negative_keyword_candidates}
          currencyCode={currencyCode}
          compact
        />
      ) : null}
      {decision.custom_segment_candidates.length > 0 ? (
        <AdsCustomSegmentCandidatesPanel candidates={decision.custom_segment_candidates} compact />
      ) : null}
      {decision.search_term_ngram_rows.length > 0 ? (
        <div className="mt-3">
          <AdsSearchTermNgramRowsTable
            rows={decision.search_term_ngram_rows}
            currencyCode={currencyCode}
            compact
          />
        </div>
      ) : null}
      {decision.campaign_triage_rows.length > 0 ? (
        <div className="mt-3">
          <AdsCampaignTriageRowsPanel
            rows={decision.campaign_triage_rows}
            currencyCode={currencyCode}
            compact
          />
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Dowody" values={decision.evidence_ids.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <LinkedTraceLine label="ActionObjecty" values={decision.action_ids} kind="actions" />
        {decision.operator_review_gates.length > 0 ? (
          <TraceLine
            label="Wymagany review"
            values={decision.operator_review_gates.map(adsOperatorReviewGateLabel)}
          />
        ) : null}
        <TraceLine label="Nie wolno twierdzić" values={decision.blocked_claims.map(adsBlockedClaimLabel)} />
      </div>
    </article>
  );
}

function AdsMetricEvidencePanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode?: string;
}) {
  const [showDiagnosticTables, setShowDiagnosticTables] = useState(false);
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
  const missingReadContracts = uniqueValues([
    ...data.account_currency_read_contract.missing_read_contracts,
    ...data.business_context_read_contract.missing_read_contracts,
    ...data.campaign_read_contract.missing_read_contracts,
    ...data.derived_kpi_read_contract.missing_read_contracts,
    ...data.budget_pacing_read_contract.missing_read_contracts,
    ...data.recommendations_read_contract.missing_read_contracts,
    ...data.impression_share_read_contract.missing_read_contracts,
    ...campaignTriage.missing_read_contracts,
    ...data.change_history_read_contract.missing_read_contracts,
    ...data.change_impact_readiness_contract.missing_read_contracts,
    ...searchTermReview.missing_read_contracts,
    ...data.search_terms_read_contract.missing_read_contracts,
    ...data.search_term_ngram_read_contract.missing_read_contracts,
    ...data.search_term_safety_read_contract.missing_read_contracts,
    ...data.keyword_match_context_read_contract.missing_read_contracts,
    ...data.custom_segments_read_contract.missing_read_contracts,
    ...data.custom_segments_read_contract.audience_forecast_read_contract.missing_read_contracts,
    ...data.negative_keywords_read_contract.missing_read_contracts
  ]).map(adsMissingReadContractLabel);
  const operatorReviewGates = uniqueValues([
    ...searchTermReview.operator_review_gates,
    ...(data.search_terms_read_contract.operator_review_gates ?? []),
    ...data.search_term_ngram_read_contract.operator_review_gates,
    ...data.search_term_safety_read_contract.operator_review_gates,
    ...data.keyword_match_context_read_contract.operator_review_gates,
    ...data.custom_segments_read_contract.operator_review_gates,
    ...data.custom_segments_read_contract.audience_forecast_read_contract.operator_review_gates,
    ...data.decision_queue.flatMap((decision) => decision.operator_review_gates)
  ]).map(adsOperatorReviewGateLabel);
  const blockedClaims = uniqueValues([
    ...data.account_currency_read_contract.blocked_claims,
    ...data.business_context_read_contract.blocked_claims,
    ...data.campaign_read_contract.blocked_claims,
    ...data.derived_kpi_read_contract.blocked_claims,
    ...data.budget_pacing_read_contract.blocked_claims,
    ...data.recommendations_read_contract.blocked_claims,
    ...data.impression_share_read_contract.blocked_claims,
    ...campaignTriage.blocked_claims,
    ...data.change_history_read_contract.blocked_claims,
    ...data.change_impact_readiness_contract.blocked_claims,
    ...searchTermReview.blocked_claims,
    ...data.search_terms_read_contract.blocked_claims,
    ...data.search_term_ngram_read_contract.blocked_claims,
    ...data.search_term_safety_read_contract.blocked_claims,
    ...data.keyword_match_context_read_contract.blocked_claims,
    ...data.custom_segments_read_contract.blocked_claims,
    ...data.custom_segments_read_contract.audience_forecast_read_contract.blocked_claims,
    ...data.negative_keywords_read_contract.blocked_claims,
    ...data.sections.flatMap((section) => section.blocked_claims)
  ]).map(adsBlockedClaimLabel);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót kontraktu WILQ API. Decyzje dla marketera są powyżej;
            tutaj widać kampanie, zapytania i blokady claimów.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
          <MetricTile label="Kampanie" value={campaignRows.length} />
          <MetricTile label="KPI" value={derivedKpiRows.length} />
          <MetricTile label="Budżety" value={budgetRows.length} />
          <MetricTile label="Wspólne budżety" value={sharedBudgetRows.length} />
          <MetricTile label="Rekom." value={recommendationRows.length} />
          <MetricTile label="Udział" value={impressionShareRows.length} />
          <MetricTile label="Triage" value={campaignTriageRows.length} />
          <MetricTile label="Zmiany" value={changeHistoryRows.length} />
          <MetricTile label="Review zapytań" value={searchTermReview.total_search_term_count} />
          <MetricTile label="Zapytania" value={searchTermRows.length} />
          <MetricTile label="N-gramy" value={searchTermNgramRows.length} />
          <MetricTile label="Safety 90d" value={searchTermSafetyRows.length} />
          <MetricTile label="Keywords" value={keywordContextRows.length} />
          <MetricTile label="Review wykl." value={negativeKeywordCandidates.length} />
          <MetricTile label="Segmenty" value={customSegmentCandidates.length} />
          <MetricTile label="Waluta" value={currencyCode ?? "brak"} />
          <MetricTile
            label="Biznes"
            value={adsBusinessContextStatusValue(data.business_context_read_contract)}
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
          <AdsBudgetPacingRowsTable rows={budgetRows} currencyCode={currencyCode} />
          <AdsSharedBudgetDistributionPanel
            rows={sharedBudgetRows}
            currencyCode={currencyCode}
          />
          <AdsRecommendationRowsPanel
            rows={recommendationRows}
            currencyCode={currencyCode}
          />
          <AdsImpressionShareRowsTable rows={impressionShareRows} />
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
        <TraceLine label="Brakujące kontrakty" values={missingReadContracts} />
        <TraceLine label="Wymaga review" values={operatorReviewGates} empty="brak" />
        <TraceLine label="Nie wolno twierdzić" values={blockedClaims} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine
          label="Sekcje źródłowe"
          values={data.sections.map((section) => adsSectionLabel(section.id))}
        />
      </div>
    </section>
  );
}

function AdsBusinessTargetInterpretationPanel({
  contract
}: {
  contract: AdsDiagnosticsResponse["business_context_read_contract"];
}) {
  const interpretation = contract.target_interpretation;
  const strategyReadiness = contract.strategy_review_readiness_contract;
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-ink">Interpretacja celu biznesowego Ads</h3>
          <p className="mt-1 text-slate-700">{interpretation.summary}</p>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          {interpretation.interpretation_contract} / {interpretation.status}
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Wolno użyć jako"
          values={interpretation.allowed_uses.map(adsBusinessUseLabel)}
          empty="brak"
        />
        <TraceLine
          label="Zablokowane użycia"
          values={interpretation.blocked_uses.map(adsBusinessUseLabel)}
          empty="brak"
        />
        <TraceLine
          label="Braki"
          values={interpretation.missing_requirements.map(adsMissingReadContractLabel)}
          empty="brak"
        />
        <TraceLine
          label="Polityki"
          values={interpretation.policy_ids}
          empty="brak"
        />
        <LinkedTraceLine
          label="ActionObjecty"
          values={interpretation.action_ids}
          kind="actions"
          empty="brak"
        />
      </div>
      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold text-ink">
              Gotowość strategy review Ads
            </h4>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              {strategyReadiness.summary}
            </p>
          </div>
          <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
            {adsDecisionStatusLabel(strategyReadiness.status)} /{" "}
            {adsStrategyReviewStatusLabel(strategyReadiness.latest_review_status)}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
          <MetricTile
            label="Marża"
            value={adsStrategyContextValue(strategyReadiness.current_context.profit_margin)}
          />
          <MetricTile
            label="Target ROAS"
            value={adsStrategyContextValue(strategyReadiness.current_context.target_roas)}
          />
          <MetricTile
            label="Target CPA"
            value={adsStrategyContextValue(strategyReadiness.current_context.target_cpa_micros)}
          />
          <MetricTile label="Braki" value={strategyReadiness.missing_read_contracts.length} />
          <MetricTile label="Review" value={adsStrategyReviewStatusLabel(strategyReadiness.latest_review_status)} />
        </div>
        <p className="mt-3 text-xs font-medium text-ink">{strategyReadiness.next_step}</p>
        <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
          <TraceLine
            label="Wymagana walidacja"
            values={strategyReadiness.required_validation.map(adsOperatorReviewGateLabel)}
            empty="brak"
          />
          <TraceLine
            label="Braki"
            values={strategyReadiness.missing_read_contracts.map(adsMissingReadContractLabel)}
            empty="brak"
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={strategyReadiness.blocked_claims.map(adsBlockedClaimLabel)}
            empty="brak"
          />
          <LinkedTraceLine
            label="ActionObjecty"
            values={strategyReadiness.action_ids}
            kind="actions"
            empty="brak"
          />
        </div>
      </div>
    </div>
  );
}

function AdsCampaignRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsCampaignMetricRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wymiarowych wierszy kampanii. Ads Doctor nie może analizować kampanii bez odczytu Google Ads." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Review</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-4 font-semibold">Wartość konw.</th>
            <th className="py-2 pr-4 font-semibold">Powód</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-xs">
                <div className="font-semibold text-ink">
                  {row.review_priority} / {row.review_score}
                </div>
                <div className="mt-1 text-slate-500">
                  {row.human_review_gates.slice(0, 2).map(adsOperatorReviewGateLabel).join(", ")}
                </div>
                {row.target_status !== "no_target" ? (
                  <div className="mt-1 text-slate-500">{row.target_status_label}</div>
                ) : null}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversion_value)}</td>
              <td className="max-w-md py-2 pr-4 text-xs leading-5 text-slate-600">
                {row.review_reason}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsCampaignTriageRowsPanel({
  rows,
  contract,
  currencyCode,
  compact = false
}: {
  rows: AdsCampaignTriageRow[];
  contract?: AdsDiagnosticsResponse["campaign_triage_read_contract"];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kolejki triage kampanii. WILQ potrzebuje campaign activity, KPI, budżetu i kontraktów review, żeby ustalić kolejność sprawdzania." />
    );
  }

  const visibleRows = compact ? rows.slice(0, 3) : rows.slice(0, 8);

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Kolejność review kampanii</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {contract?.summary ??
              "Ranking kampanii do ręcznego review. To nie jest werdykt waste, CPA, ROAS ani profitability."}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Kampanie" value={rows.length} />
          <MetricTile
            label="Pilne"
            value={rows.filter((row) => row.review_priority === "pilne").length}
          />
          <MetricTile
            label="Wysokie"
            value={rows.filter((row) => row.review_priority === "wysokie").length}
          />
        </div>
      </div>

      <div className="grid gap-2">
        {visibleRows.map((row) => (
          <article
            key={`${row.campaign_id ?? row.campaign_name}-triage`}
            className="rounded-md border border-line bg-white p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{row.campaign_name}</h4>
                <p className="mt-1 text-xs text-slate-500">
                  {row.advertising_channel_type ?? "kanał: brak"} /{" "}
                  {row.campaign_status ?? "status: brak"} / {row.target_status_label}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {row.review_priority} / score {row.review_score}
              </span>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
              <MetricTile label="Kliknięcia" value={adsNumber(row.clicks)} />
              <MetricTile label="Koszt" value={adsCost(row.cost_micros, currencyCode)} />
              <MetricTile label="Konwersje" value={adsNumber(row.conversions)} />
              <MetricTile label="ROAS" value={adsNumber(row.roas)} />
              <MetricTile
                label="Wydanie 7d"
                value={adsPercent(row.spend_to_budget_ratio_7d)}
              />
            </div>

            <p className="mt-3 text-xs leading-5 text-slate-700">{row.review_reason}</p>
            <p className="mt-2 text-xs font-medium text-ink">{row.next_step}</p>
            <div className="mt-3 grid gap-1 text-xs text-slate-600 md:grid-cols-2">
              <TraceLine
                label="Wymagany review"
                values={row.human_review_gates.slice(0, 4).map(adsOperatorReviewGateLabel)}
                empty="brak"
              />
              <TraceLine
                label="Braki"
                values={row.missing_read_contracts.map(adsMissingReadContractLabel)}
                empty="brak"
              />
              <LinkedTraceLine
                label="Dowody"
                values={row.evidence_ids.slice(0, 3)}
                kind="evidence"
              />
              <LinkedTraceLine
                label="ActionObjecty"
                values={row.action_ids}
                kind="actions"
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsDerivedKpiRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsDerivedKpiRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wyliczalnych KPI kampanii. WILQ potrzebuje kosztu, kliknięć, konwersji i wartości konwersji w campaign facts." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">CTR</th>
            <th className="py-2 pr-4 font-semibold">Śr. CPC</th>
            <th className="py-2 pr-4 font-semibold">Conv. rate</th>
            <th className="py-2 pr-4 font-semibold">CPA</th>
            <th className="py-2 pr-4 font-semibold">Target CPA</th>
            <th className="py-2 pr-4 font-semibold">Różnica CPA</th>
            <th className="py-2 pr-4 font-semibold">ROAS</th>
            <th className="py-2 pr-4 font-semibold">Target ROAS</th>
            <th className="py-2 pr-4 font-semibold">Różnica ROAS</th>
            <th className="py-2 pr-4 font-semibold">Triage</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}-kpi`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">{adsPercent(row.ctr)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.average_cpc_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsPercent(row.conversion_rate)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_per_conversion_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.target_cpa_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsSignedCost(row.cpa_vs_target_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.roas)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.target_roas)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsSignedNumber(row.roas_vs_target)}</td>
              <td className="py-2 pr-4 text-xs">
                <span className={adsTargetStatusClass(row.target_status)}>
                  {row.target_status_label}
                </span>
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claims.slice(0, 2).map(adsBlockedClaimLabel).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsBudgetPacingRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsBudgetPacingRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kontekstu budżetu kampanii. WILQ potrzebuje campaign_budget.amount_micros z Google Ads, żeby pokazać koszt względem budżetu dziennego." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Budżet</th>
            <th className="py-2 pr-4 font-semibold">Koszt 7 dni</th>
            <th className="py-2 pr-4 font-semibold">7-dniowy budżet</th>
            <th className="py-2 pr-4 font-semibold">Wydanie</th>
            <th className="py-2 pr-4 font-semibold">Rekomendacja Google</th>
            <th className="py-2 pr-4 font-semibold">Preview apply</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.budget_id ?? row.budget_name}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                <div>{row.campaign_name}</div>
                <div className="text-xs font-normal text-slate-500">
                  {row.advertising_channel_type ?? "kanał: brak"} /{" "}
                  {row.budget_period ?? "okres: brak"}
                </div>
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.budget_amount_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_7d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.seven_day_budget_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.spend_to_budget_ratio_7d)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.has_recommended_budget
                  ? adsCost(row.recommended_budget_amount_micros, currencyCode)
                  : "brak"}
              </td>
              <td className="min-w-48 py-2 pr-4 text-xs text-slate-600">
                {row.payload_preview ? (
                  <div>
                    <div className="font-semibold text-ink">
                      {adsCost(
                        row.payload_preview.proposed_budget_amount_micros,
                        currencyCode
                      )}
                    </div>
                    <div>
                      {row.payload_preview.operation_type} /{" "}
                      {row.payload_preview.apply_allowed ? "apply możliwy" : "apply zablokowany"}
                    </div>
                    <div className="mt-1 text-slate-500">
                      Safety: {row.payload_preview.safety_review.safety_contract} /{" "}
                      {row.payload_preview.safety_review.apply_allowed
                        ? "mutation ready"
                        : "blocked"}
                    </div>
                    <div className="text-slate-500">
                      Braki:{" "}
                      {row.payload_preview.safety_review.missing_requirements
                        .slice(0, 2)
                        .join(", ") || "brak"}
                    </div>
                  </div>
                ) : (
                  "brak"
                )}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claims.slice(0, 2).map(adsBlockedClaimLabel).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsSharedBudgetDistributionPanel({
  rows,
  currencyCode
}: {
  rows: AdsSharedBudgetDistributionRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="rounded-md border border-line bg-slate-50 p-3 text-sm text-slate-600">
        Brak wspólnych budżetów w bieżącym odczycie albo każda kampania ma osobny
        budżet. To oznacza, że WILQ nie musi rozdzielać kosztu shared budget między
        kilka kampanii przed review.
      </div>
    );
  }
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Podział wspólnych budżetów</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Wspólne budget_id z Google Ads rozbite po kampaniach. To jest kontekst
            review, nie rekomendacja skalowania ani zmiany budżetu.
          </p>
        </div>
        <MetricTile label="Wspólne budżety" value={rows.length} />
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {rows.slice(0, 6).map((row) => (
          <article key={row.budget_id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">
                  {row.budget_name ?? row.budget_id}
                </h4>
                <p className="mt-1 text-xs text-slate-500">
                  budget_id={row.budget_id} / kampanie={row.campaign_count}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                wydanie: {adsPercent(row.spend_to_budget_ratio_7d)}
              </span>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
              <MetricTile
                label="Budżet dzień"
                value={adsCost(row.budget_amount_micros, currencyCode)}
              />
              <MetricTile
                label="Budżet 7 dni"
                value={adsCost(row.seven_day_budget_micros, currencyCode)}
              />
              <MetricTile
                label="Koszt 7 dni"
                value={adsCost(row.total_cost_micros_7d, currencyCode)}
              />
            </div>
            <div className="mt-3 grid gap-2">
              {row.campaign_shares.slice(0, 8).map((share) => (
                <div
                  key={`${row.budget_id}-${share.campaign_id ?? share.campaign_name}`}
                  className="rounded-md border border-line bg-slate-50 p-2 text-xs"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="font-semibold text-ink">{share.campaign_name}</div>
                      <div className="mt-1 text-slate-500">
                        {share.advertising_channel_type ?? "kanał: brak"} /{" "}
                        {share.campaign_status ?? "status: brak"}
                      </div>
                    </div>
                    <div className="text-right text-slate-700">
                      <div>{adsCost(share.cost_micros_7d, currencyCode)}</div>
                      <div className="text-slate-500">
                        udział: {adsPercent(share.spend_share_7d)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 grid gap-1 text-xs text-slate-600">
              <LinkedTraceLine
                label="Dowody"
                values={row.evidence_ids.slice(0, 3)}
                kind="evidence"
              />
              <TraceLine
                label="Nie wolno twierdzić"
                values={row.blocked_claims.map(adsBlockedClaimLabel)}
              />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsRecommendationRowsPanel({
  rows,
  currencyCode
}: {
  rows: AdsRecommendationRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak aktywnych rekomendacji Google Ads w ostatnim read-only odczycie albo brak kontraktu recommendations. WILQ nie przyjmuje rekomendacji bez review." />
    );
  }
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Rekomendacje Google Ads</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Read-only lista typów rekomendacji do review. Apply pozostaje zablokowany.
          </p>
        </div>
        <MetricTile label="Do review" value={rows.length} />
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {rows.slice(0, 6).map((row) => (
          <article
            key={`${row.recommendation_id ?? row.recommendation_type}-${row.campaign_id ?? "account"}`}
            className="rounded-md border border-line bg-white p-3"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-ink">
                  {row.recommendation_type}
                </div>
                <div className="mt-1 text-xs leading-5 text-slate-600">
                  Kampania: {row.campaign_id ?? "brak"} / budżet:{" "}
                  {row.campaign_budget_id ?? "brak"} / zakres kampanii:{" "}
                  {row.campaign_count ?? 0}
                </div>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {row.review_priority} / {row.review_score}
              </span>
            </div>
            <div className="mt-1 text-xs leading-5 text-slate-600">
              {row.review_reason}
            </div>
            {row.impact_available ? (
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                <MetricTile label="Klik. delta" value={adsSignedNumber(row.delta_clicks)} />
                <MetricTile
                  label="Wyśw. delta"
                  value={adsSignedNumber(row.delta_impressions)}
                />
                <MetricTile
                  label="Koszt delta"
                  value={adsSignedCost(row.delta_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Koszt bazowy"
                  value={adsCost(row.base_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Koszt po"
                  value={adsCost(row.potential_cost_micros, currencyCode)}
                />
                <MetricTile
                  label="Konw. delta"
                  value={adsSignedNumber(row.delta_conversions)}
                />
              </div>
            ) : (
              <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-800">
                Google Ads nie zwrócił impact metrics dla tego typu rekomendacji.
              </div>
            )}
            <TraceLine
              label="Review człowieka"
              values={row.human_review_gates}
              empty="brak"
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={row.blocked_claims.map(adsBlockedClaimLabel)}
            />
            <LinkedTraceLine
              label="Dowody"
              values={row.evidence_ids.slice(0, 2)}
              kind="evidence"
            />
            {row.payload_preview ? (
              <div className="mt-3 rounded-md border border-line bg-slate-50 px-2 py-2 text-xs text-slate-700">
                <div className="font-semibold text-ink">Podgląd apply: zablokowany</div>
                <div className="mt-1">
                  Operacja: {row.payload_preview.operation_type}. Wdrożenie:{" "}
                  {row.payload_preview.apply_allowed
                    ? "dozwolone"
                    : "niedozwolone bez review i audytu"}.
                </div>
                <div className="mt-1">
                  Walidacje: {row.payload_preview.required_validation.slice(0, 4).join(", ")}
                </div>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsImpressionShareRowsTable({ rows }: { rows: AdsImpressionShareRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wierszy udziału w wyświetleniach. WILQ nie może ocenić utraconej ekspozycji przez budżet albo ranking bez impression share facts." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Search IS</th>
            <th className="py-2 pr-4 font-semibold">Lost IS budget</th>
            <th className="py-2 pr-4 font-semibold">Lost IS rank</th>
            <th className="py-2 pr-3 font-semibold">Blokady</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name}-impression-share`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.campaign_name}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_impression_share)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_budget_lost_impression_share)}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsPercent(row.search_rank_lost_impression_share)}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claims.slice(0, 2).map(adsBlockedClaimLabel).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsChangeHistoryRowsTable({ rows }: { rows: AdsChangeHistoryRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wierszy historii zmian. WILQ nie może łączyć performance ze zmianami kampanii bez change_event facts." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Data zmiany</th>
            <th className="py-2 pr-4 font-semibold">Zasób</th>
            <th className="py-2 pr-4 font-semibold">Operacja</th>
            <th className="py-2 pr-4 font-semibold">Klient</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-3 font-semibold">Pola</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr key={`${row.change_event_id ?? "unknown"}-${row.change_date_time ?? "no-date"}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                {row.change_date_time ?? "brak daty"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.change_resource_type ?? "brak"} / {row.change_resource_id ?? "brak ID"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.resource_change_operation ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{row.client_type ?? "brak"}</td>
              <td className="py-2 pr-4 text-slate-700">{row.campaign_id ?? "brak"}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.changed_fields.length > 0
                  ? row.changed_fields.slice(0, 4).join(", ")
                  : `${row.changed_field_count ?? 0} pól`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsChangeImpactReadinessPanel({
  contract,
  currencyCode
}: {
  contract: AdsDiagnosticsResponse["change_impact_readiness_contract"];
  currencyCode?: string;
}) {
  const rows = contract.readiness_rows;
  const currentReadoutCount = rows.filter((row) => row.current_campaign_metrics_available).length;

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Gotowość impact review zmian</h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            {contract.summary}
          </p>
          <p className="mt-2 text-xs font-medium text-ink">{contract.next_step}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Zmiany" value={rows.length} />
          <MetricTile label="Odczyty" value={currentReadoutCount} />
          <MetricTile label="Status" value={adsDecisionStatusLabel(contract.status)} />
        </div>
      </div>

      {rows.length === 0 ? (
        <BlockerNotice message="Brak change_event rows do impact review. WILQ może pokazać tylko blocker, nie ocenę wpływu zmian." />
      ) : (
        <div className="grid gap-2">
          {rows.slice(0, 6).map((row) => (
            <AdsChangeImpactReadinessCard
              key={`${row.change_event_id ?? "change"}-${row.campaign_id ?? "campaign"}`}
              row={row}
              currencyCode={currencyCode}
            />
          ))}
        </div>
      )}

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Metryki dostępne"
          values={contract.allowed_metrics.map(adsAllowedMetricLabel)}
          empty="brak"
        />
        <TraceLine
          label="Brakujące kontrakty"
          values={contract.missing_read_contracts.map(adsMissingReadContractLabel)}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={contract.blocked_claims.map(adsBlockedClaimLabel)}
          empty="brak"
        />
        <LinkedTraceLine
          label="Dowody"
          values={contract.evidence_ids.slice(0, 6)}
          kind="evidence"
          empty="brak"
        />
      </div>
    </div>
  );
}

function AdsChangeImpactReadinessCard({
  row,
  currencyCode
}: {
  row: AdsChangeImpactReadinessRow;
  currencyCode?: string;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-ink">
            {row.campaign_name ?? row.campaign_id ?? "kampania bez nazwy"}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {row.change_event_id ?? "brak change ID"} / {row.change_date_time ?? "brak daty"}
          </p>
        </div>
        <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
          {row.current_campaign_metrics_available ? "odczyt kampanii" : "brak odczytu"}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
        <MetricTile label="Kliknięcia" value={adsNumber(row.current_clicks)} />
        <MetricTile label="Wyświetlenia" value={adsNumber(row.current_impressions)} />
        <MetricTile label="Koszt" value={adsCost(row.current_cost_micros, currencyCode)} />
        <MetricTile label="Konwersje" value={adsNumber(row.current_conversions)} />
        <MetricTile label="Wartość konw." value={adsNumber(row.current_conversion_value)} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Zmienione pola"
          values={row.changed_fields}
          empty="brak pól"
        />
        <TraceLine
          label="Braki"
          values={row.missing_read_contracts.map(adsMissingReadContractLabel)}
          empty="brak"
        />
        <TraceLine
          label="Blokady"
          values={row.blocked_claims.map(adsBlockedClaimLabel)}
          empty="brak"
        />
        <LinkedTraceLine label="Dowody" values={row.evidence_ids} kind="evidence" empty="brak" />
      </div>
    </article>
  );
}

function AdsSearchTermReviewSummaryPanel({
  contract,
  currencyCode
}: {
  contract: AdsDiagnosticsResponse["search_term_review_summary_contract"];
  currencyCode?: string;
}) {
  if (contract.status === "blocked") {
    return <BlockerNotice message={contract.summary} />;
  }

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Kolejność review zapytań</h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {contract.summary}
          </p>
          <p className="mt-1 text-sm font-medium text-ink">{contract.next_step}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile label="Zapytania" value={contract.total_search_term_count} />
          <MetricTile label="Zero conv." value={contract.zero_conversion_search_term_count} />
          <MetricTile label="Kliknięcia" value={contract.total_clicks} />
          <MetricTile label="Koszt" value={adsCost(contract.total_cost_micros, currencyCode)} />
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Kampanie do przejrzenia
          </h4>
          <div className="mt-2 overflow-x-auto rounded-md border border-line bg-white">
            <table className="min-w-full text-left text-xs">
              <thead className="border-b border-line bg-slate-50 uppercase tracking-normal text-slate-500">
                <tr>
                  <th className="py-2 pl-3 pr-3 font-semibold">Kampania</th>
                  <th className="py-2 pr-3 font-semibold">Zapytania</th>
                  <th className="py-2 pr-3 font-semibold">Zero conv.</th>
                  <th className="py-2 pr-3 font-semibold">Koszt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {contract.campaign_review_rows.slice(0, 6).map((row) => (
                  <tr key={`${row.campaign_id ?? "unknown"}-${row.campaign_name ?? "campaign"}`}>
                    <td className="py-2 pl-3 pr-3 font-medium text-ink">
                      {row.campaign_name ?? row.campaign_id ?? "brak"}
                    </td>
                    <td className="py-2 pr-3 text-slate-700">{row.search_term_count}</td>
                    <td className="py-2 pr-3 text-slate-700">
                      {row.zero_conversion_search_term_count}
                    </td>
                    <td className="py-2 pr-3 text-slate-700">
                      {adsCost(row.cost_micros, currencyCode)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h4 className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Top kosztowe zapytania
          </h4>
          <div className="mt-2 grid gap-2">
            {contract.top_cost_search_terms.slice(0, 5).map((row) => (
              <div
                key={`${row.search_term}-${row.campaign_id ?? "unknown"}-${
                  row.ad_group_id ?? "unknown"
                }`}
                className="rounded-md border border-line bg-white p-2"
              >
                <div className="text-sm font-medium text-ink">{row.search_term}</div>
                <div className="mt-1 text-xs text-slate-600">
                  {row.campaign_name ?? row.campaign_id ?? "brak kampanii"} / koszt{" "}
                  {adsCost(row.cost_micros, currencyCode)} / konwersje{" "}
                  {adsNumber(row.conversions)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Wymaga review"
          values={contract.operator_review_gates.map(adsOperatorReviewGateLabel)}
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={contract.blocked_claims.map(adsBlockedClaimLabel)}
        />
      </div>
    </div>
  );
}

function AdsSearchTermRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsSearchTermMetricRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak wymiarowych wierszy zapytań. Ads Doctor nie może analizować zapytań ani waste bez danych z search_term_view." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Zapytanie</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`${row.search_term}-${row.campaign_id ?? "unknown"}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.search_term}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_name ?? row.campaign_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_name ?? row.ad_group_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsSearchTermNgramRowsTable({
  rows,
  currencyCode,
  compact = false
}: {
  rows: AdsSearchTermNgramRow[];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak n-gramów zapytań. WILQ musi najpierw mieć search-term rows z Google Ads." />
    );
  }
  const visibleRows = rows.slice(0, compact ? 5 : 12);
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Temat z zapytań</th>
            <th className="py-2 pr-4 font-semibold">Źródłowe query</th>
            <th className="py-2 pr-4 font-semibold">Przykłady</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {visibleRows.map((row) => (
            <tr key={`${row.ngram_size}-${row.ngram}`}>
              <td className="py-2 pl-3 pr-4 font-medium text-ink">
                {row.ngram}
                <span className="ml-2 text-xs font-normal text-slate-500">
                  {row.ngram_size}-gram
                </span>
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {adsNumber(row.source_search_term_count)}
              </td>
              <td className="max-w-sm py-2 pr-4 text-xs leading-5 text-slate-600">
                {row.sample_search_terms.join(", ")}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsSearchTermSafetyRowsTable({
  rows,
  currencyCode
}: {
  rows: AdsSearchTermSafetyRow[];
  currencyCode?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak 90-dniowego safety read dla zapytań. WILQ nie powinien zdejmować blokady z review wykluczeń bez tego odczytu." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Safety 90 dni</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-4 font-semibold">Kliknięcia</th>
            <th className="py-2 pr-4 font-semibold">Wyświetlenia</th>
            <th className="py-2 pr-4 font-semibold">Koszt</th>
            <th className="py-2 pr-4 font-semibold">Konwersje</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`90d-${row.search_term}-${row.campaign_id ?? "unknown"}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.search_term}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_name ?? row.campaign_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_name ?? row.ad_group_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_90d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions_90d)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">{row.evidence_ids.length} ID</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsKeywordMatchContextRowsTable({ rows }: { rows: AdsKeywordMatchContextRow[] }) {
  if (rows.length === 0) {
    return (
      <BlockerNotice message="Brak kontekstu istniejących keywords/match types. WILQ nie powinien zdejmować blokady z review wykluczeń bez odczytu ad_group_criterion." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Keyword</th>
            <th className="py-2 pr-4 font-semibold">Match type</th>
            <th className="py-2 pr-4 font-semibold">Status</th>
            <th className="py-2 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Grupa reklam</th>
            <th className="py-2 pr-3 font-semibold">Dowody</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.slice(0, 12).map((row) => (
            <tr
              key={`kw-${row.criterion_id ?? row.keyword_text}-${
                row.ad_group_id ?? "unknown"
              }`}
            >
              <td className="py-2 pl-3 pr-4 font-medium text-ink">{row.keyword_text}</td>
              <td className="py-2 pr-4 text-slate-700">{row.match_type}</td>
              <td className="py-2 pr-4 text-slate-700">
                {row.negative ? "negative" : row.criterion_status ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_name ?? row.campaign_id ?? "brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_name ?? row.ad_group_id ?? "brak"}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_ids.length} ID
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AdsNegativeKeywordCandidatesPanel({
  candidates,
  currencyCode,
  compact = false
}: {
  candidates: AdsNegativeKeywordCandidate[];
  currencyCode?: string;
  compact?: boolean;
}) {
  if (candidates.length === 0) {
    return compact ? null : (
      <BlockerNotice message="Brak kolejki review wykluczeń. WILQ potrzebuje search terms z aktywnością i zerową konwersją, a potem 90-dniowego safety checku." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Review wykluczeń z search terms
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest kolejka bezpieczeństwa. WILQ pokazuje terminy do sprawdzenia,
            ale blokuje wdrożenie wykluczeń bez kontekstu dopasowania, 90-dniowej
            historii i walidacji ActionObject.
          </p>
        </div>
      ) : null}
      <div className={compact ? "grid gap-2" : "grid gap-3 md:grid-cols-2"}>
        {candidates.slice(0, compact ? 2 : 6).map((candidate) => (
          <article key={candidate.id} className="rounded-md border border-line bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <h4 className="text-sm font-semibold text-ink">{candidate.search_term}</h4>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {candidate.campaign_name ?? candidate.campaign_id ?? "kampania"} /{" "}
                  {candidate.ad_group_name ?? candidate.ad_group_id ?? "grupa reklam"}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {candidate.review_priority} / {candidate.review_score}
              </span>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {candidate.review_reason}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Safety:{" "}
              {candidate.safety_status === "needs_90_day_review"
                ? "wymaga 90 dni"
                : candidate.safety_status === "read_ready_needs_human_review"
                  ? "90 dni odczytane"
                  : "blocked"}
            </p>
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
              <MetricTile label="Kliknięcia" value={adsNumber(candidate.clicks)} />
              <MetricTile
                label="Koszt"
                value={adsCost(candidate.cost_micros, currencyCode)}
              />
              <MetricTile label="Konwersje" value={adsNumber(candidate.conversions)} />
              <MetricTile label="Klik. 90d" value={adsNumber(candidate.clicks_90d)} />
              <MetricTile
                label="Koszt 90d"
                value={adsCost(candidate.cost_micros_90d, currencyCode)}
              />
              <MetricTile label="Konw. 90d" value={adsNumber(candidate.conversions_90d)} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{candidate.next_step}</p>
            {candidate.payload_preview ? (
              <div className="mt-2 rounded-md border border-blue-100 bg-blue-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-blue-700">
                  Podgląd wykluczenia
                </div>
                <div>
                  `{candidate.payload_preview.negative_keyword_text}` /{" "}
                  {candidate.payload_preview.match_type} /{" "}
                  {adsNegativeKeywordLevelLabel(candidate.payload_preview.level)}
                </div>
                <div className="text-slate-600">
                  Wdrożenie:{" "}
                  {candidate.payload_preview.apply_allowed
                    ? "wymaga walidacji"
                    : "zablokowany"}
                  . {candidate.payload_preview.reason}
                </div>
              </div>
            ) : null}
            {candidate.keyword_context_rows.length > 0 ? (
              <div className="mt-2 rounded-md border border-line bg-slate-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-slate-600">
                  Istniejące keywords w tej grupie
                </div>
                {candidate.keyword_context_rows.slice(0, 4).map((row) => (
                  <div key={`${row.criterion_id ?? row.keyword_text}-${row.match_type}`}>
                    {row.keyword_text} / {row.match_type}
                    {row.negative ? " / negative" : ""}
                  </div>
                ))}
              </div>
            ) : null}
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Review człowieka"
                values={candidate.human_review_gates}
                empty="brak"
              />
              <TraceLine label="Wymagane checki" values={candidate.required_checks.map(adsMissingReadContractLabel)} />
              <LinkedTraceLine
                label="Dowody"
                values={uniqueValues([
                  ...candidate.evidence_ids,
                  ...candidate.safety_evidence_ids
                ]).slice(0, 3)}
                kind="evidence"
              />
              <TraceLine label="Nie wolno twierdzić" values={candidate.blocked_claims.map(adsBlockedClaimLabel)} />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsBlockedHandoffPanel({ handoff }: { handoff: AdsBlockedHandoff }) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Handoff blockera Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{handoff.title}</h2>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          {adsDecisionStatusLabel(handoff.status)}
        </span>
      </div>
      <p className="text-sm leading-6 text-slate-700">{handoff.summary}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600">{handoff.marketer_message}</p>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Ścieżka naprawy</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {handoff.repair_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Co wolno pokazać w demo</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
            {handoff.allowed_demo_claims.map((claim) => (
              <li key={claim}>{claim}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <LinkedTraceLine label="Dowody" values={handoff.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={handoff.source_connectors} />
        <LinkedTraceLine label="ActionObjecty" values={handoff.action_ids} kind="actions" />
        <TraceLine label="Nie wolno twierdzić" values={handoff.blocked_claims.map(adsBlockedClaimLabel)} />
      </div>
    </section>
  );
}

function adsDecisionTypeLabel(decisionType: AdsDecisionItem["decision_type"]) {
  if (decisionType === "review_campaign_activity") return "przegląd kampanii";
  if (decisionType === "review_business_context") return "kontekst biznesowy";
  if (decisionType === "review_derived_kpi") return "wyliczone KPI";
  if (decisionType === "review_budget_context") return "kontekst budżetu";
  if (decisionType === "review_recommendations") return "rekomendacje do review";
  if (decisionType === "review_impression_share") return "udział w wyświetleniach";
  if (decisionType === "review_change_history") return "historia zmian";
  if (decisionType === "review_campaign_triage") return "kolejność review kampanii";
  if (decisionType === "review_search_term_safety") return "safety 90 dni";
  if (decisionType === "review_search_terms") return "przegląd zapytań";
  if (decisionType === "review_search_term_ngrams") return "tematy zapytań";
  if (decisionType === "review_negative_keyword_safety") return "review wykluczeń";
  if (decisionType === "prepare_custom_segments") return "kandydaci segmentów";
  if (decisionType === "block_write_actions") return "blokada zmian";
  return "naprawa dostępu";
}

function adsDecisionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  return status;
}

function adsNegativeKeywordLevelLabel(level: string) {
  if (level === "ad_group") return "grupa reklam";
  if (level === "campaign_review_required") return "poziom do decyzji";
  return level;
}

function adsRiskLabel(risk: AdsDecisionItem["risk"]) {
  if (risk === "critical") return "krytyczne";
  if (risk === "high") return "wysokie";
  if (risk === "medium") return "średnie";
  return "niskie";
}

function adsConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function adsRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function adsSectionLabel(sectionId: string) {
  if (sectionId === "ads_live_data_status") return "Status odczytu Google Ads";
  if (sectionId === "ads_campaign_overview") return "Aktywność kampanii";
  if (sectionId === "ads_business_context") return "Kontekst biznesowy";
  if (sectionId === "ads_derived_kpi") return "Wyliczone KPI";
  if (sectionId === "ads_budget_pacing") return "Kontekst budżetu";
  if (sectionId === "ads_recommendations") return "Rekomendacje Google Ads";
  if (sectionId === "ads_impression_share") return "Udział w wyświetleniach";
  if (sectionId === "ads_change_history") return "Historia zmian";
  if (sectionId === "ads_search_terms") return "Zapytania użytkowników";
  if (sectionId === "ads_search_term_ngrams") return "N-gramy zapytań";
  if (sectionId === "ads_search_term_safety") return "Safety 90 dni";
  if (sectionId === "ads_keyword_match_context") return "Kontekst keywords";
  if (sectionId === "ads_negative_keyword_safety") return "Review wykluczeń";
  if (sectionId === "ads_custom_segments") return "Custom segments";
  if (sectionId === "ads_action_safety") return "Bezpieczeństwo akcji Ads";
  if (sectionId === "ads_oauth_blocker") return "Dostęp Google Ads";
  return sectionId;
}

function adsBusinessContextStatusValue(
  contract: AdsDiagnosticsResponse["business_context_read_contract"]
) {
  if (contract.status === "blocked") return "blokada";
  if (contract.missing_read_contracts.includes("target_roas_or_cpa")) return "wstępny";
  return "gotowe";
}

function adsBusinessUseLabel(value: string) {
  const labels: Record<string, string> = {
    campaign_review_context: "kontekst review kampanii",
    budget_review_context: "kontekst review budżetu",
    human_strategy_review_context: "kontekst strategii człowieka",
    margin_context: "kontekst marży",
    business_goal_alignment: "dopasowanie do celu biznesowego",
    budget_goal_guardrail: "guardrail celu budżetu",
    target_roas_review: "review target ROAS",
    target_cpa_review: "review target CPA",
    profitability_verdict: "werdykt rentowności",
    target_kpi_verdict: "werdykt KPI targetu",
    budget_scaling: "skalowanie budżetu",
    budget_apply: "zmiana budżetu",
    recommendation_apply: "wdrożenie rekomendacji",
    wasted_budget_claim: "claim wasted budget",
    automatic_scaling: "automatyczne skalowanie",
    profitability_verdict_without_value_model_review:
      "werdykt rentowności bez review modelu wartości"
  };
  return labels[value] ?? value;
}

function adsAllowedMetricLabel(value: string) {
  const labels: Record<string, string> = {
    clicks: "kliknięcia",
    impressions: "wyświetlenia",
    cost_micros: "koszt",
    conversions: "konwersje",
    conversion_value: "wartość konwersji",
    account_currency_code: "waluta konta",
    profit_margin: "marża",
    business_goal: "cel biznesowy",
    human_budget_goal: "cel budżetu",
    target_roas: "target ROAS",
    target_cpa_micros: "target CPA",
    budget_amount_micros: "budżet",
    cost_micros_7d: "koszt 7 dni",
    seven_day_budget_micros: "budżet 7 dni",
    spend_to_budget_ratio_7d: "wydanie względem budżetu",
    budget_has_recommended_budget: "sygnał recommended budget",
    budget_recommended_amount_micros: "rekomendowany budżet",
    recommendation_available: "rekomendacja dostępna",
    recommendation_campaign_count: "kampanie w rekomendacji",
    recommendation_impact_base_clicks: "bazowe kliknięcia rekomendacji",
    recommendation_impact_potential_clicks: "potencjalne kliknięcia rekomendacji",
    recommendation_impact_base_impressions: "bazowe wyświetlenia rekomendacji",
    recommendation_impact_potential_impressions:
      "potencjalne wyświetlenia rekomendacji",
    recommendation_impact_base_cost_micros: "bazowy koszt rekomendacji",
    recommendation_impact_potential_cost_micros: "potencjalny koszt rekomendacji",
    recommendation_impact_base_conversions: "bazowe konwersje rekomendacji",
    recommendation_impact_potential_conversions:
      "potencjalne konwersje rekomendacji",
    recommendation_impact_base_conversion_value:
      "bazowa wartość konwersji rekomendacji",
    recommendation_impact_potential_conversion_value:
      "potencjalna wartość konwersji rekomendacji",
    search_impression_share: "udział w wyświetleniach",
    search_budget_lost_impression_share: "utracony udział przez budżet",
    search_rank_lost_impression_share: "utracony udział przez ranking",
    change_event_available: "historia zmian dostępna",
    change_event_changed_field_count: "liczba zmienionych pól",
    current_campaign_clicks: "bieżące kliknięcia kampanii",
    current_campaign_impressions: "bieżące wyświetlenia kampanii",
    current_campaign_cost_micros: "bieżący koszt kampanii",
    current_campaign_conversions: "bieżące konwersje kampanii",
    current_campaign_conversion_value: "bieżąca wartość konwersji kampanii",
    search_term: "zapytanie",
    ngram: "temat zapytania",
    ngram_size: "długość tematu",
    source_search_term_count: "liczba źródłowych zapytań",
    sample_search_terms: "przykłady zapytań",
    search_term_90d_clicks: "kliknięcia 90 dni",
    search_term_90d_impressions: "wyświetlenia 90 dni",
    search_term_90d_cost_micros: "koszt 90 dni",
    search_term_90d_conversions: "konwersje 90 dni",
    search_term_90d_conversion_value: "wartość konwersji 90 dni",
    keyword_text: "keyword",
    keyword_match_type: "typ dopasowania keyworda",
    criterion_status: "status keyworda",
    keyword_negative: "keyword negative",
    campaign: "kampania",
    ad_group: "grupa reklam",
    status: "status zapytania"
  };
  return labels[value] ?? value;
}

function adsOptimizerReadinessItemLabel(value: string) {
  const labels: Record<string, string> = {
    campaign_review_queue: "kampanie do review",
    budget_and_recommendation_review: "budżety i rekomendacje",
    search_terms_review_queue: "search terms",
    negative_keyword_review_queue: "negative keywords",
    custom_segments_review_queue: "custom segments",
    keyword_planner_enrichment: "Keyword Planner",
    change_history_impact_review: "historia zmian",
    ads_apply_safety_gate: "apply safety gate"
  };
  return labels[value] ?? value;
}

function adsStrategyReviewStatusLabel(value: string) {
  const labels: Record<string, string> = {
    missing: "brak review",
    approved_for_prepare: "zatwierdzone do prepare",
    needs_changes: "wymaga zmian",
    rejected: "odrzucone",
    deferred: "odroczone"
  };
  return labels[value] ?? value;
}

function adsStrategyContextValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "brak";
  if (typeof value === "number") return adsNumber(value);
  return String(value);
}

function adsOperatorReviewGateLabel(value: string) {
  const labels: Record<string, string> = {
    human_strategy_review: "review strategii przez człowieka",
    review_recommendation_type: "sprawdzenie typu rekomendacji",
    review_impact_metrics: "sprawdzenie impact metrics",
    review_change_history: "sprawdzenie historii zmian",
    review_business_goal: "sprawdzenie celu biznesowego",
    configure_business_goal: "uzupełnienie celu biznesowego",
    review_profit_margin_model: "sprawdzenie modelu marży",
    configure_profit_margin_or_value_model: "uzupełnienie marży albo modelu wartości",
    review_human_budget_goal: "sprawdzenie celu budżetu",
    configure_human_budget_goal: "uzupełnienie celu budżetu",
    confirm_target_roas_or_cpa: "potwierdzenie targetu ROAS albo CPA",
    review_target_fit: "sprawdzenie dopasowania do targetu",
    review_campaign_goal: "sprawdzenie celu kampanii",
    review_conversion_quality: "sprawdzenie jakości konwersji",
    review_budget_context: "sprawdzenie kontekstu budżetu",
    review_search_terms_before_budget_decision: "search terms przed decyzją budżetową",
    review_conversion_tracking: "sprawdzenie trackingu konwersji",
    review_pmax_asset_feed_context: "sprawdzenie PMax/feed/assets",
    review_draft_campaign_status: "sprawdzenie statusu draftu",
    recommendation_apply_preview: "podgląd apply rekomendacji",
    google_ads_rmf_compliance_review: "review Google Ads RMF/compliance",
    human_confirm_before_apply: "potwierdzenie człowieka przed wdrożeniem",
    negative_keyword_action_validation: "walidacja ActionObject dla wykluczeń",
    human_intent_review: "ręczny review intencji",
    review_source_terms: "sprawdzenie source terms",
    reject_brand_or_low_intent_terms: "odrzucenie brand/low intent terms",
    keyword_planner_enrichment: "enrichment Keyword Planner",
    forecast_or_audience_size: "forecast albo audience size"
  };
  return labels[value] ?? value;
}

function adsNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  return new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 4 }).format(value);
}

function adsCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "brak";
  const accountUnits = value / 1_000_000;
  if (currencyCode) {
    return new Intl.NumberFormat("pl-PL", {
      currency: currencyCode,
      maximumFractionDigits: 2,
      style: "currency"
    }).format(accountUnits);
  }
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    accountUnits
  )} jedn. konta`;
}

function adsSignedCost(value: number | null | undefined, currencyCode?: string) {
  if (value === null || value === undefined) return "brak";
  const formatted = adsCost(Math.abs(value), currencyCode);
  if (value > 0) return `+${formatted}`;
  if (value < 0) return `-${formatted}`;
  return formatted;
}

function adsSignedNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  if (value > 0) return `+${adsNumber(value)}`;
  return adsNumber(value);
}

function adsTargetStatusClass(status: string | null | undefined) {
  const base = "inline-flex whitespace-nowrap rounded border px-2 py-1 font-semibold";
  if (status === "spend_without_conversions") {
    return `${base} border-amber-200 bg-amber-50 text-amber-800`;
  }
  if (status === "outside_target") {
    return `${base} border-rose-200 bg-rose-50 text-rose-800`;
  }
  if (status === "within_target") {
    return `${base} border-emerald-200 bg-emerald-50 text-emerald-800`;
  }
  return `${base} border-slate-200 bg-slate-50 text-slate-600`;
}

function adsPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "brak";
  return `${new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(
    value * 100
  )}%`;
}


function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
