import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  ActionObject,
  AdsDiagnosticsResponse,
  getActions,
  getAdsDiagnosticsSummary,
  getConnectors
} from "../lib/api";
import { adsCost, adsNumber } from "../lib/adsFormatting";
import {
  BlockerNotice,
  LoadingBand,
  MetricTile,
  PlainChipRow
} from "../components/OperatorPrimitives";
import {
  AdsCustomSegmentAudienceForecastPanel,
  AdsCustomSegmentCandidatesPanel
} from "../components/AdsCustomSegmentPanels";
import {
  AdsCampaignRowsTable,
  AdsCampaignTriageRowsPanel,
  AdsDerivedKpiRowsTable
} from "../components/AdsCampaignPanels";
import {
  AdsBudgetPacingRowsTable,
  AdsChangeHistoryRowsTable,
  AdsImpressionShareRowsTable,
  AdsRecommendationRowsPanel,
  AdsSharedBudgetDistributionPanel
} from "../components/AdsBudgetRecommendationPanels";
import {
  AdsBusinessTargetInterpretationPanel,
  AdsChangeImpactReadinessPanel
} from "../components/AdsBusinessReadinessPanels";
import { AdsOperatorSummary } from "../components/AdsOperatorSummaryPanels";
import { AdsNegativeKeywordCandidatesPanel } from "../components/AdsNegativeKeywordCandidatesPanel";
import {
  AdsKeywordMatchContextRowsTable,
  AdsSearchTermNgramRowsTable,
  AdsSearchTermReviewSummaryPanel,
  AdsSearchTermRowsTable,
  AdsSearchTermSafetyRowsTable
} from "../components/AdsSearchTermPanels";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { ActionFocus } from "./ActionPanels";

type AdsBlockedHandoff = NonNullable<AdsDiagnosticsResponse["blocked_handoff"]>;
type AdsDecisionItem = AdsDiagnosticsResponse["decision_queue"][number];

const adsMissingLatestReadLabel = "bez ostatniego odczytu; nie oceniaj trendu";

export function AdsDoctorSurface() {
  const diagnostics = useQuery({
    queryKey: ["ads-diagnostics", "summary"],
    queryFn: getAdsDiagnosticsSummary
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors
  });

  if (diagnostics.isLoading || actions.isLoading || connectors.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać danych Ads. WILQ nie może udawać diagnozy bez danych." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać akcji do sprawdzenia. Odśwież widok albo sprawdź status WILQ." />
      </main>
    );
  }
  if (connectors.error || !connectors.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się pobrać statusu źródeł danych. Odśwież widok albo sprawdź status WILQ." />
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
          <h1 className="text-2xl font-semibold tracking-normal">Google Ads</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok Google Ads z WILQ. Pokazuje, co marketer może
            uczciwie sprawdzić na podstawie kampanii i zapytań oraz które wnioski
            pozostają zablokowane bez kolejnych danych.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Blokady" value={blockedDecisionCount} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
          <MetricTile label="Waluta" value={currencyCode ?? "waluta do potwierdzenia"} />
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
          <PlainChipRow
            values={[
              `${data.connector.label}: ${data.connector_status_label}`,
              data.live_data_status_label,
              latestRefresh ? `ostatni odczyt: ${data.latest_refresh_status_label}` : null
            ]}
          />
        </div>
        {latestRefresh?.errors.length ? (
          <div className="mt-3 rounded-md border border-risk/30 bg-risk/10 p-3 text-sm text-risk">
            {latestRefresh.errors[0]}
          </div>
        ) : null}
      </section>

      {data.blocked_handoff ? (
        <AdsBlockedHandoffPanel handoff={data.blocked_handoff} />
      ) : null}

      <AdsCondensedDecisionPanel data={data} currencyCode={currencyCode} />
      <AdsMarketSnapshot data={data} currencyCode={currencyCode} />
      <AdsExpandableReviewPanel data={data} currencyCode={currencyCode} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <AdsExpandableActionsPanel
            actions={routeActions}
            actionSummaryLabel={data.action_summary_label}
          />
        </div>
      ) : null}

    </main>
  );
}

function AdsExpandableActionsPanel({
  actions,
  actionSummaryLabel
}: {
  actions: ActionObject[];
  actionSummaryLabel: string;
}) {
  const [showActions, setShowActions] = useState(false);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ pokazuje dla Google Ads: {actionSummaryLabel}. Otwórz tę sekcję dopiero wtedy, gdy
            chcesz zapisać przegląd człowieka, wygenerować podgląd zmian albo
            sprawdzić warunki zapisu akcji.
          </p>
        </div>
        <MetricTile label="Akcje" value={actionSummaryLabel} />
      </div>

      <button
        type="button"
        onClick={() => setShowActions((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showActions ? "Ukryj akcje do sprawdzenia" : "Pokaż akcje do sprawdzenia"}
      </button>

      {showActions ? (
        <div className="mt-4">
          <ActionFocus actions={actions} />
        </div>
      ) : null}
    </section>
  );
}

function AdsExpandableReviewPanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
}) {
  const [showDeepReview, setShowDeepReview] = useState(false);
  const summary = data.operator_summary;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje decyzję i skrót odczytu. Rozwiń pełny przegląd,
            gdy chcesz przejrzeć gotowość obszarów, karty decyzji, zapytania,
            rekomendacje i szczegółowe dowody.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Gotowe" value={summary.ready_area_count} />
          <MetricTile label="Blokady" value={summary.blocked_area_count} />
          <MetricTile label="Akcje" value={summary.action_summary_label} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowDeepReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showDeepReview ? "Ukryj pełny przegląd Ads" : "Pokaż pełny przegląd Ads"}
      </button>

      {showDeepReview ? (
        <div className="mt-4 grid gap-6">
          <AdsOperatorSummary data={data} />
          <AdsMetricEvidencePanel data={data} currencyCode={currencyCode} />
        </div>
      ) : null}
    </section>
  );
}

function AdsCondensedDecisionPanel({
  data,
  currencyCode
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const primaryDecision =
    summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is AdsDecisionItem => Boolean(decision)) ??
    data.decision_queue[0];
  const blockedClaimSummary = primaryDecision
    ? primaryDecision.blocked_claim_summary_label
    : summary.blocked_claim_summary_label;
  const missingInputSummary = primaryDecision
    ? primaryDecision.missing_read_contract_summary_label
    : summary.missing_read_contract_summary_label;
  const evidenceSummary = primaryDecision
    ? primaryDecision.evidence_summary_label
    : summary.evidence_summary_label;
  const actionSummary = primaryDecision?.action_summary_label ?? summary.action_summary_label;

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            Decyzja skondensowana
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            {primaryDecision
              ? `Pierwszy krok: ${primaryDecision.decision_type_label}`
              : "Najpierw sprawdź Ads"}
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {primaryDecision
              ? primaryDecision.summary
              : "WILQ ma odczyt Google Ads i pokazuje, co można sprawdzić bez udawania optymalizatora."}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Kliknięcia" value={adsNumber(summary.total_clicks)} />
          <MetricTile label="Koszt" value={adsCost(summary.total_cost_micros, currencyCode)} />
          <MetricTile label="Konwersje" value={adsNumber(summary.total_conversions)} />
          <MetricTile label="Akcje" value={actionSummary} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dlaczego to ma znaczenie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {primaryDecision
              ? primaryDecision.rationale
              : "Ads ma aktualne dowody, ale decyzje budżetowe i zapis zmian nadal wymagają celów, sprawdzenia w WILQ i audytu."}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny następny krok</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-ink">
            {primaryDecision
              ? primaryDecision.next_step
              : "Przejrzyj kolejkę Ads i wybierz jedną akcję do sprawdzenia bez zapisu zmian."}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dowody i źródła</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Dowody" values={[evidenceSummary]} />
            <TraceLine label="Źródła" values={data.source_connector_labels} />
            <TraceLine
              label="Stan danych"
              values={[
                data.live_data_status_label,
                data.latest_refresh
                  ? `ostatni odczyt: ${data.latest_refresh_status_label}`
                  : adsMissingLatestReadLabel
              ]}
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Czego WILQ nie powie</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Nie wolno twierdzić" values={[blockedClaimSummary]} />
            <TraceLine label="Brakujące wejścia" values={[missingInputSummary]} />
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Jak później sprawdzimy efekt</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {primaryDecision?.measurement_plan ?? data.operator_summary.next_step}
        </p>
      </div>
    </section>
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
            Zapis zmian, ocena zmarnowanego budżetu, koszt pozyskania celu,
            zwrot z reklam i skalowanie budżetu pozostają zablokowane do czasu
            sprawdzenia w WILQ oraz uzupełnienia brakujących danych.
          </p>
        </div>
        <MetricTile label="Waluta" value={currencyCode ?? "waluta do potwierdzenia"} />
      </div>
      <div className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-600">
        Wartości Ads
      </div>
      <div className="grid gap-2 text-center text-xs sm:grid-cols-2 xl:grid-cols-5">
        <MetricTile label="Kliknięcia" value={adsNumber(summary.total_clicks)} />
        <MetricTile label="Wyświetlenia" value={adsNumber(summary.total_impressions)} />
        <MetricTile label="Koszt" value={adsCost(summary.total_cost_micros, currencyCode)} />
        <MetricTile label="Konwersje" value={adsNumber(summary.total_conversions)} />
        <MetricTile label="Wartość konwersji" value={adsNumber(summary.total_conversion_value)} />
      </div>
      <div className="mt-3 grid gap-2 text-center text-xs sm:grid-cols-3 xl:grid-cols-6">
        <MetricTile label="Kampanie" value={summary.campaign_count} />
        <MetricTile label="Zapytania" value={summary.search_term_count} />
        <MetricTile
          label="Rekomendacje"
          value={data.recommendations_read_contract.recommendation_rows.length}
        />
        <MetricTile label="Budżety" value={data.budget_pacing_read_contract.budget_rows.length} />
        <MetricTile label="Gotowe" value={summary.ready_area_count} />
        <MetricTile label="Blokady" value={summary.blocked_area_count} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Brakujące dane"
          values={[summary.missing_read_contract_summary_label]}
          empty="dane kompletne"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={[summary.blocked_claim_summary_label]}
          empty="WILQ nie zgłosił dodatkowych zablokowanych obietnic."
        />
      </div>
    </section>
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

function AdsBlockedHandoffPanel({
  handoff
}: {
  handoff: AdsBlockedHandoff;
}) {
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przekazanie blokady Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{handoff.title}</h2>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          {handoff.status_label}
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
        <TraceLine label="Dowody" values={[handoff.evidence_summary_label]} />
        <TraceLine label="Źródła" values={handoff.source_connector_labels} />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[handoff.action_summary_label]}
          empty="WILQ nie podał akcji do sprawdzenia; zostaje ręczny przegląd Ads."
        />
        <TraceLine label="Nie wolno twierdzić" values={handoff.blocked_claim_labels} />
      </div>
    </section>
  );
}
