import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  ActionObject,
  AdsDiagnosticsResponse,
  ConnectorStatus,
  getActions,
  getAdsDiagnosticsSummary,
  getConnectors
} from "../lib/api";
import { connectorLabelsFromStatuses } from "../lib/connectorLabels";
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
        <BlockerNotice message="Nie udało się odczytać danych Ads. Ads Doctor nie może udawać diagnozy bez WILQ." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. Ads Doctor nie może pokazać sprawdzenia ani podglądu akcji." />
      </main>
    );
  }
  if (connectors.error || !connectors.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/connectors. Ads Doctor nie może pokazać źródeł danych językiem marketera." />
      </main>
    );
  }

  const data = diagnostics.data;
  const connectorStatuses = connectors.data;
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
            Dedykowany widok Google Ads z WILQ. Pokazuje, co marketer może
            uczciwie sprawdzić na podstawie kampanii i zapytań oraz które wnioski
            pozostają zablokowane bez kolejnych kontraktów odczytu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Blokady" value={blockedDecisionCount} />
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
              {data.connector.label}: {adsConnectorStatusLabel(data.connector.status)}
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

      {data.blocked_handoff ? (
        <AdsBlockedHandoffPanel handoff={data.blocked_handoff} connectorStatuses={connectorStatuses} />
      ) : null}

      <AdsCondensedDecisionPanel data={data} currencyCode={currencyCode} connectorStatuses={connectorStatuses} />
      <AdsMarketSnapshot data={data} currencyCode={currencyCode} />
      <AdsExpandableReviewPanel data={data} currencyCode={currencyCode} connectorStatuses={connectorStatuses} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <AdsExpandableActionsPanel actions={routeActions} />
        </div>
      ) : null}

    </main>
  );
}

function AdsExpandableActionsPanel({ actions }: { actions: ActionObject[] }) {
  const [showActions, setShowActions] = useState(false);
  const actionCountLabel = formatActionObjectCount(actions.length);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ ma {actionCountLabel} dla Ads. Otwórz je dopiero wtedy, gdy
            chcesz zapisać przegląd człowieka, wygenerować podgląd zmian albo
            sprawdzić techniczne warunki akcji.
          </p>
        </div>
        <MetricTile label="Akcje" value={actionCountLabel} />
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
          <ActionObjectFocus actions={actions} />
        </div>
      ) : null}
    </section>
  );
}

function AdsExpandableReviewPanel({
  data,
  currencyCode,
  connectorStatuses
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
  connectorStatuses: ConnectorStatus[];
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
          <MetricTile label="Akcje" value={formatActionObjectCount(summary.action_ids.length)} />
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
          <AdsOperatorSummary data={data} connectorStatuses={connectorStatuses} />
          <AdsMetricEvidencePanel data={data} currencyCode={currencyCode} />
        </div>
      ) : null}
    </section>
  );
}

function AdsCondensedDecisionPanel({
  data,
  currencyCode,
  connectorStatuses
}: {
  data: AdsDiagnosticsResponse;
  currencyCode: string | undefined;
  connectorStatuses: ConnectorStatus[];
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const primaryDecision =
    summary.top_decision_ids
      .map((decisionId) => decisionsById.get(decisionId))
      .find((decision): decision is AdsDecisionItem => Boolean(decision)) ??
    data.decision_queue[0];
  const blockedClaims = primaryDecision
    ? primaryDecision.blocked_claims.map(adsBlockedClaimLabel)
    : summary.blocked_claims.map(adsBlockedClaimLabel);
  const missingInputs = primaryDecision
    ? primaryDecision.missing_read_contracts.map(adsMissingReadContractLabel)
    : summary.missing_read_contracts.map(adsMissingReadContractLabel);
  const evidenceCount = primaryDecision?.evidence_ids.length ?? summary.evidence_ids.length;
  const actionCount = primaryDecision?.action_ids.length ?? summary.action_ids.length;
  const sourceConnectors = connectorLabelsFromStatuses(
    primaryDecision?.source_connectors ?? summary.source_connectors,
    connectorStatuses
  );

  return (
    <section className="mb-6 rounded-md border border-action/30 bg-action/5 p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-action">
            Decyzja skondensowana
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-normal text-ink">
            {primaryDecision
              ? `Pierwszy krok: ${adsDecisionTypeLabel(primaryDecision.decision_type)}`
              : "Najpierw sprawdź Ads"}
          </h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
            {primaryDecision
              ? adsDecisionSummary(primaryDecision)
              : "WILQ ma odczyt Google Ads i pokazuje, co można sprawdzić bez udawania optymalizatora."}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          <MetricTile label="Kliknięcia" value={adsNumber(summary.total_clicks)} />
          <MetricTile label="Koszt" value={adsCost(summary.total_cost_micros, currencyCode)} />
          <MetricTile label="Konwersje" value={adsNumber(summary.total_conversions)} />
          <MetricTile label="Akcje" value={formatActionObjectCount(actionCount)} />
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dlaczego to ma znaczenie</h3>
          <p className="mt-2 text-sm leading-6 text-slate-700">
            {primaryDecision
              ? adsDecisionRationale(primaryDecision)
              : "Ads ma live evidence, ale decyzje budżetowe i zapis zmian nadal wymagają targetów, sprawdzenia w WILQ i audytu."}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny następny krok</h3>
          <p className="mt-2 text-sm font-medium leading-6 text-ink">
            {primaryDecision
              ? adsDecisionNextStep(primaryDecision)
              : "Przejrzyj kolejkę Ads i wybierz jedną akcję do sprawdzenia bez zapisu zmian."}
          </p>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Dowody i źródła</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Dowody" values={[formatTraceIdCount(evidenceCount)]} />
            <TraceLine label="Źródła" values={sourceConnectors} />
            <TraceLine
              label="Stan danych"
              values={[
                data.live_data_available ? "metryki Ads dostępne" : "brak metryk Ads",
                data.latest_refresh
                  ? `ostatni odczyt: ${adsRefreshStatusLabel(data.latest_refresh.status)}`
                  : "brak odczytu"
              ]}
            />
          </div>
        </div>
        <div className="rounded-md border border-line bg-white p-3">
          <h3 className="text-sm font-semibold text-ink">Czego WILQ nie powie</h3>
          <div className="mt-2 grid gap-1 text-xs leading-5 text-slate-600">
            <TraceLine label="Nie wolno twierdzić" values={blockedClaims.slice(0, 6)} />
            <TraceLine label="Brakujące wejścia" values={missingInputs.slice(0, 6)} />
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <h3 className="text-sm font-semibold text-ink">Jak później sprawdzimy efekt</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          {adsCondensedMeasurementPlan(primaryDecision)}
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
            Zapis zmian, ocena zmarnowanego budżetu, werdykty CPA/ROAS
            i skalowanie budżetu pozostają zablokowane do czasu sprawdzenia w WILQ
            oraz brakujących kontraktów.
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
        <MetricTile label="Gotowe" value={summary.ready_area_count} />
        <MetricTile label="Blokady" value={summary.blocked_area_count} />
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

function AdsOperatorSummary({
  data,
  connectorStatuses
}: {
  data: AdsDiagnosticsResponse;
  connectorStatuses: ConnectorStatus[];
}) {
  const currencyCode = data.account_currency_read_contract.currency_code ?? undefined;
  const optimizer = data.optimizer_readiness_contract;
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const decisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is AdsDecisionItem => Boolean(decision));
  const allowedMetrics = summary.allowed_metrics.map(adsAllowedMetricLabel);
  const missingReadContracts = summary.missing_read_contracts.map(adsMissingReadContractLabel);
  const operatorReviewGates = summary.operator_review_gate_labels;
  const blockedClaims = summary.blocked_claims.map(adsBlockedClaimLabel);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{summary.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ porządkuje bieżący odczyt Ads w kolejkę decyzji: kampanie,
            wyszukiwane hasła, KPI, budżety i rekomendacje. To jest przegląd
            oparty o dowody, bez zapisu zmian i bez werdyktu o opłacalności.
          </p>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-ink">
            Przejrzyj top decyzje w tej kolejności. Nie zapisuj wykluczeń,
            budżetów ani rekomendacji bez podglądu zmian, sprawdzenia w WILQ
            i oceny kontekstu biznesowego.
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
          <MetricTile label="Gotowe" value={summary.ready_area_count} />
          <MetricTile label="Blokady" value={summary.blocked_area_count} />
        </div>
      </div>

      <AdsOptimizerReadinessPanel contract={optimizer} />
      <AdsStartHerePanel decisions={decisions.slice(0, 3)} currencyCode={currencyCode} />

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {decisions.length > 0 ? (
            decisions.map((decision) => (
              <AdsDecisionCard
                key={decision.id}
                decision={decision}
                currencyCode={currencyCode}
                connectorStatuses={connectorStatuses}
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
            <TraceLine label="Wymagana ocena" values={operatorReviewGates} empty="brak" />
            <TraceLine
              label="Dowody"
              values={[formatTraceIdCount(summary.evidence_ids.length)]}
              empty="brak"
            />
            <TraceLine
              label="Akcje WILQ"
              values={[formatActionObjectCount(summary.action_ids.length)]}
              empty="brak"
            />
            <TraceLine label="Nie wolno twierdzić" values={blockedClaims} empty="brak" />
          </div>
        </div>
      </div>
    </section>
  );
}

function AdsStartHerePanel({
  decisions,
  currencyCode
}: {
  decisions: AdsDecisionItem[];
  currencyCode?: string;
}) {
  if (decisions.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 rounded-md border border-line bg-white p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Najpierw sprawdź w Ads</h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-600">
            Skrócona kolejność dla marketera. Pełne karty i akcje do sprawdzenia są niżej,
            ale ten pasek pokazuje, od czego zacząć bez przechodzenia przez całą listę.
          </p>
        </div>
        <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
          tryb: sprawdzenie przed zapisem zmian
        </span>
      </div>
      <div className="grid gap-2 lg:grid-cols-3">
        {decisions.map((decision, index) => (
          <article key={decision.id} className="rounded-md border border-line bg-slate-50 p-3">
            <div className="flex items-start gap-2">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-ink text-xs font-semibold text-white">
                {index + 1}
              </span>
              <div>
                <div className="text-sm font-semibold leading-5 text-ink">
                  Krok {index + 1}: {adsDecisionTitle(decision)}
                </div>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {adsDecisionTypeLabel(decision.decision_type)} / {adsDecisionStatusLabel(decision.status)}
                </p>
              </div>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">
              {adsStartHereSummary(decision, currencyCode)}
            </p>
            <p className="mt-2 text-xs font-medium leading-5 text-ink">
              {adsDecisionNextStep(decision)}
            </p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Akcje"
                values={[formatActionObjectCount(decision.action_ids.length)]}
                empty="brak"
              />
              <TraceLine
                label="Nie wolno"
                values={decision.blocked_claims.map(adsBlockedClaimLabel).slice(0, 3)}
                empty="brak"
              />
            </div>
          </article>
        ))}
      </div>
    </div>
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
            WILQ ma obszary gotowe do ręcznej oceny i obszary nadal zablokowane.
            Ten panel pokazuje, co można przejrzeć teraz, a czego nie wolno
            jeszcze zamienić w decyzję albo zapis zmian.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Gotowe" value={contract.ready_area_count} />
          <MetricTile label="Zablokowane" value={contract.blocked_area_count} />
          <MetricTile label="Tryb" value={adsOptimizerModeLabel(contract.mode)} />
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <AdsOptimizerReadinessGroup
          title="Gotowe do oceny"
          items={readyItems}
          empty="Brak obszarów gotowych do oceny."
        />
        <AdsOptimizerReadinessGroup
          title="Zablokowane wnioski i zapis zmian"
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
        <TraceLine
          label="Dowody"
          values={[formatTraceIdCount(contract.evidence_ids.length)]}
          empty="brak"
        />
        <TraceLine
          label="Akcje WILQ"
          values={[formatActionObjectCount(contract.action_ids.length)]}
          empty="brak"
        />
      </div>
    </div>
  );
}

function formatTraceIdCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 ID";
  return `${count} ID`;
}

function formatActionObjectCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 akcja do sprawdzenia";
  if (count >= 2 && count <= 4) return `${count} akcje do sprawdzenia`;
  return `${count} akcji do sprawdzenia`;
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
                <p className="mt-1 text-xs text-slate-500">
                  {adsOptimizerReadinessTitle(item.id, item.title)}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {adsDecisionStatusLabel(item.status)} / {adsRiskLabel(item.risk)}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">
              {adsOptimizerReadinessSummary(item.id, item.summary)}
            </p>
            <p className="mt-2 text-xs font-medium text-ink">
              {adsOptimizerReadinessNextStep(item.id, item.next_step)}
            </p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Kontrakty"
                values={[formatTraceIdCount(item.source_contract_ids.length)]}
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
  currencyCode,
  connectorStatuses
}: {
  decision: AdsDecisionItem;
  currencyCode?: string;
  connectorStatuses: ConnectorStatus[];
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{adsDecisionTitle(decision)}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {adsDecisionTypeLabel(decision.decision_type)} / {adsDecisionStatusLabel(decision.status)}
          </p>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          ryzyko: {adsRiskLabel(decision.risk)}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {adsDecisionSummary(decision)}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        {adsDecisionRationale(decision)}
      </p>
      <p className="mt-2 text-sm font-medium text-ink">
        {adsDecisionNextStep(decision)}
      </p>
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
        <TraceLine
          label="Dowody"
          values={[formatTraceIdCount(decision.evidence_ids.length)]}
          empty="brak"
        />
        <TraceLine label="Źródła" values={connectorLabelsFromStatuses(decision.source_connectors, connectorStatuses)} />
        <TraceLine
          label="Akcje WILQ"
          values={[formatActionObjectCount(decision.action_ids.length)]}
          empty="brak"
        />
        {decision.operator_review_gate_labels.length > 0 ? (
          <TraceLine
            label="Wymagana ocena"
            values={decision.operator_review_gate_labels}
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
  const missingReadContracts = summary.missing_read_contracts.map(adsMissingReadContractLabel);
  const operatorReviewGates = summary.operator_review_gate_labels;
  const blockedClaims = summary.blocked_claims.map(adsBlockedClaimLabel);

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Ads
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót źródeł i blokad w WILQ. Decyzje dla marketera są powyżej;
            tutaj widać kampanie, zapytania i twierdzenia, których nie wolno używać.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-5">
          <MetricTile label="Kampanie" value={campaignRows.length} />
          <MetricTile label="KPI" value={derivedKpiRows.length} />
          <MetricTile label="Budżety" value={budgetRows.length} />
          <MetricTile label="Wspólne budżety" value={sharedBudgetRows.length} />
          <MetricTile label="Rekom." value={recommendationRows.length} />
          <MetricTile label="Udział" value={impressionShareRows.length} />
          <MetricTile label="Kolejka oceny" value={campaignTriageRows.length} />
          <MetricTile label="Zmiany" value={changeHistoryRows.length} />
          <MetricTile label="Ocena zapytań" value={searchTermReview.total_search_term_count} />
          <MetricTile label="Zapytania" value={searchTermRows.length} />
          <MetricTile label="N-gramy" value={searchTermNgramRows.length} />
          <MetricTile label="Safety 90d" value={searchTermSafetyRows.length} />
          <MetricTile label="Keywords" value={keywordContextRows.length} />
          <MetricTile label="Ocena wykl." value={negativeKeywordCandidates.length} />
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
        <TraceLine label="Wymaga oceny" values={operatorReviewGates} empty="brak" />
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
          values={[formatTraceIdCount(interpretation.policy_ids.length)]}
          empty="brak"
        />
        <TraceLine
          label="Akcje WILQ"
          values={[formatActionObjectCount(interpretation.action_ids.length)]}
          empty="brak"
        />
      </div>
      <div className="mt-3 rounded-md border border-line bg-white p-3">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold text-ink">
              Gotowość oceny strategii Ads
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
            label="Docelowy zwrot z reklam"
            value={adsStrategyContextValue(strategyReadiness.current_context.target_roas)}
          />
          <MetricTile
            label="Docelowy koszt pozyskania celu"
            value={adsStrategyContextValue(strategyReadiness.current_context.target_cpa_micros)}
          />
          <MetricTile label="Braki" value={strategyReadiness.missing_read_contracts.length} />
          <MetricTile label="Ocena" value={adsStrategyReviewStatusLabel(strategyReadiness.latest_review_status)} />
        </div>
        <p className="mt-3 text-xs font-medium text-ink">{strategyReadiness.next_step}</p>
        <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
          <TraceLine
            label="Wymagane sprawdzenie"
            values={[formatTraceIdCount(strategyReadiness.required_validation.length)]}
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
          <TraceLine
            label="Akcje WILQ"
            values={[formatActionObjectCount(strategyReadiness.action_ids.length)]}
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
            <th className="py-2 pr-4 font-semibold">Ocena</th>
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
                  {row.human_review_gate_labels.slice(0, 2).join(", ")}
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
                {adsCampaignReviewReason(row, currencyCode)}
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
      <BlockerNotice message="Brak kolejki oceny kampanii. WILQ potrzebuje aktywności kampanii, KPI, budżetu i kontraktów oceny, żeby ustalić kolejność sprawdzania." />
    );
  }

  const visibleRows = compact ? rows.slice(0, 3) : rows.slice(0, 8);

  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Kolejność oceny kampanii</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {contract?.summary ??
              "Ranking kampanii do ręcznej oceny. To nie jest werdykt o zmarnowanym budżecie, CPA, ROAS ani opłacalności."}
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
                  {row.review_priority} / wynik {row.review_score}
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

            <p className="mt-3 text-xs leading-5 text-slate-700">
              {adsCampaignTriageReason(row, currencyCode)}
            </p>
            <p className="mt-2 text-xs font-medium text-ink">
              {adsCampaignTriageNextStep(row)}
            </p>
            <div className="mt-3 grid gap-1 text-xs text-slate-600 md:grid-cols-2">
              <TraceLine
                label="Wymagana ocena"
                values={row.human_review_gate_labels.slice(0, 4)}
                empty="brak"
              />
              <TraceLine
                label="Braki"
                values={row.missing_read_contracts.map(adsMissingReadContractLabel)}
                empty="brak"
              />
              <TraceLine
                label="Dowody"
                values={[formatTraceIdCount(row.evidence_ids.length)]}
                empty="brak"
              />
              <TraceLine
                label="Akcje WILQ"
                values={[formatActionObjectCount(row.action_ids.length)]}
                empty="brak"
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
            <th className="py-2 pr-4 font-semibold">Docelowy koszt pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">Różnica CPA</th>
            <th className="py-2 pr-4 font-semibold">ROAS</th>
            <th className="py-2 pr-4 font-semibold">Docelowy zwrot z reklam</th>
            <th className="py-2 pr-4 font-semibold">Różnica ROAS</th>
            <th className="py-2 pr-4 font-semibold">Ocena</th>
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
            <th className="py-2 pr-4 font-semibold">Podgląd zmian</th>
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
                      {adsGoogleOperationLabel(row.payload_preview.operation_type)} /{" "}
                      {row.payload_preview.apply_allowed
                        ? "wymaga sprawdzenia"
                        : "zapis zmian zablokowany"}
                    </div>
                    <div className="mt-1 text-slate-500">
                      Bezpieczeństwo budżetu:{" "}
                      {row.payload_preview.safety_review.apply_allowed
                        ? "gotowe do sprawdzenia"
                        : "zablokowane"}
                    </div>
                    <div className="text-slate-500">
                      Braki:{" "}
                      {formatTraceIdCount(
                        row.payload_preview.safety_review.missing_requirements.length
                      )}
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
        budżet. To oznacza, że WILQ nie musi rozdzielać kosztu wspólnego budżetu
        między kilka kampanii przed oceną.
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
            oceny, nie rekomendacja skalowania ani zmiany budżetu.
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
      <BlockerNotice message="Brak aktywnych rekomendacji Google Ads w ostatnim odczycie tylko do analizy albo brak kontraktu rekomendacji. WILQ nie przyjmuje rekomendacji bez ręcznej oceny." />
    );
  }
  return (
    <div className="rounded-md border border-line bg-slate-50 p-3">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Rekomendacje Google Ads</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Lista typów rekomendacji do sprawdzenia. Zapis zmian pozostaje
            zablokowany do czasu sprawdzenia w WILQ i audytu.
          </p>
        </div>
        <MetricTile label="Do oceny" value={rows.length} />
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
              {adsRecommendationReviewReason(row, currencyCode)}
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
                Google Ads nie zwrócił metryk wpływu dla tego typu rekomendacji.
              </div>
            )}
            <TraceLine
              label="Ocena człowieka"
              values={row.human_review_gate_labels}
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
                <div className="font-semibold text-ink">Podgląd zmian: zablokowany</div>
                <div className="mt-1">
                  Operacja: {adsGoogleOperationLabel(row.payload_preview.operation_type)}.
                  Zapis zmian:{" "}
                  {row.payload_preview.apply_allowed
                    ? "dozwolone"
                    : "niedozwolone bez oceny i audytu"}.
                </div>
                <div className="mt-1">
                  Warunki sprawdzenia: {formatTraceIdCount(row.payload_preview.required_validation.length)}.
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
      <BlockerNotice message="Brak wierszy historii zmian. WILQ nie może łączyć skuteczności ze zmianami kampanii bez faktów change_event." />
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
          <h3 className="text-sm font-semibold text-ink">Gotowość oceny wpływu zmian</h3>
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
        <BlockerNotice message="Brak zdarzeń historii zmian do oceny wpływu. WILQ może pokazać tylko blocker, nie ocenę wpływu zmian." />
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
          <h3 className="text-sm font-semibold text-ink">Kolejność oceny zapytań</h3>
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
          label="Wymaga oceny"
          values={contract.operator_review_gate_labels}
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
      <BlockerNotice message="Brak n-gramów zapytań. WILQ musi najpierw mieć wiersze wyszukiwanych haseł z Google Ads." />
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
      <BlockerNotice message="Brak 90-dniowego odczytu bezpieczeństwa dla zapytań. WILQ nie powinien zdejmować blokady z oceny wykluczeń bez tego odczytu." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Bezpieczeństwo 90 dni</th>
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
      <BlockerNotice message="Brak kontekstu istniejących słów kluczowych i typów dopasowania. WILQ nie powinien zdejmować blokady z oceny wykluczeń bez odczytu ad_group_criterion." />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Słowo kluczowe</th>
            <th className="py-2 pr-4 font-semibold">Typ dopasowania</th>
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
                {row.negative ? "wykluczające" : row.criterion_status ?? "brak"}
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
      <BlockerNotice message="Brak kolejki oceny wykluczeń. WILQ potrzebuje wyszukiwanych haseł z aktywnością i zerową konwersją, a potem 90-dniowej kontroli bezpieczeństwa." />
    );
  }
  return (
    <div className={compact ? "mt-3 grid gap-2" : "rounded-md border border-line bg-slate-50 p-3"}>
      {!compact ? (
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-ink">
            Ocena wykluczeń z wyszukiwanych haseł
          </h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            To jest kolejka bezpieczeństwa. WILQ pokazuje terminy do sprawdzenia,
            ale blokuje zapis wykluczeń bez kontekstu dopasowania, 90-dniowej
            historii i sprawdzenia w WILQ.
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
              {adsNegativeKeywordReason(candidate, currencyCode)}
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-600">
              Bezpieczeństwo:{" "}
              {candidate.safety_status === "needs_90_day_review"
                ? "wymaga 90 dni"
                : candidate.safety_status === "read_ready_needs_human_review"
                  ? "90 dni odczytane"
                  : "zablokowane"}
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
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {adsNegativeKeywordNextStep(candidate)}
            </p>
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
                  Zapis zmian:{" "}
                  {candidate.payload_preview.apply_allowed
                    ? "wymaga sprawdzenia"
                    : "zablokowane"}
                  . {adsNegativeKeywordPayloadReason(candidate.payload_preview.reason)}
                </div>
              </div>
            ) : null}
            {candidate.keyword_context_rows.length > 0 ? (
              <div className="mt-2 rounded-md border border-line bg-slate-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-slate-600">
                  Istniejące słowa kluczowe w tej grupie
                </div>
                {candidate.keyword_context_rows.slice(0, 4).map((row) => (
                  <div key={`${row.criterion_id ?? row.keyword_text}-${row.match_type}`}>
                    {row.keyword_text} / {row.match_type}
                    {row.negative ? " / wykluczające" : ""}
                  </div>
                ))}
              </div>
            ) : null}
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Ocena człowieka"
                values={candidate.human_review_gate_labels}
                empty="brak"
              />
              <TraceLine label="Wymagane kontrole" values={candidate.required_checks.map(adsMissingReadContractLabel)} />
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

function AdsBlockedHandoffPanel({
  handoff,
  connectorStatuses
}: {
  handoff: AdsBlockedHandoff;
  connectorStatuses: ConnectorStatus[];
}) {
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
        <TraceLine label="Źródła" values={connectorLabelsFromStatuses(handoff.source_connectors, connectorStatuses)} />
        <TraceLine
          label="Akcje WILQ"
          values={[formatActionObjectCount(handoff.action_ids.length)]}
          empty="brak"
        />
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
  if (decisionType === "review_recommendations") return "rekomendacje do oceny";
  if (decisionType === "review_impression_share") return "udział w wyświetleniach";
  if (decisionType === "review_change_history") return "historia zmian";
  if (decisionType === "review_campaign_triage") return "kolejność oceny kampanii";
  if (decisionType === "review_search_term_safety") return "kontrola 90 dni";
  if (decisionType === "review_search_terms") return "przegląd zapytań";
  if (decisionType === "review_search_term_ngrams") return "tematy zapytań";
  if (decisionType === "review_negative_keyword_safety") return "ocena wykluczeń";
  if (decisionType === "prepare_custom_segments") return "segmenty do sprawdzenia";
  if (decisionType === "block_write_actions") return "blokada zmian";
  return "naprawa dostępu";
}

function adsDecisionTitle(decision: AdsDecisionItem) {
  const titles: Partial<Record<AdsDecisionItem["decision_type"], string>> = {
    review_budget_context: "Sprawdź kontekst budżetu kampanii",
    review_business_context: "Potwierdź kontekst biznesowy Ads",
    review_campaign_activity: "Przejrzyj aktywność kampanii Google Ads",
    review_campaign_triage: "Ustal kolejność oceny kampanii Ads",
    review_recommendations: "Przejrzyj rekomendacje Google Ads bez zapisu zmian",
    review_derived_kpi: "Sprawdź wyliczone KPI bez werdyktu CPA/ROAS",
    review_search_terms: "Przejrzyj wyszukiwane hasła bez automatycznych wykluczeń"
  };
  return titles[decision.decision_type] ?? decision.title;
}

function adsOptimizerModeLabel(mode: string) {
  if (mode === "review_only") return "ocena bez zapisu";
  if (mode === "read_only") return "tylko odczyt";
  if (mode === "apply_blocked") return "zapis zmian zablokowany";
  return mode;
}

function adsOptimizerReadinessTitle(id: string, fallback: string) {
  const titles: Record<string, string> = {
    ads_apply_safety_gate: "Zmiany w Google Ads",
    budget_and_recommendation_review: "Budżety, rekomendacje i udział w wyświetleniach",
    campaign_review_queue: "Kolejność sprawdzania kampanii",
    change_history_impact_review: "Historia zmian i wpływ na wyniki",
    custom_segments_review_queue: "Segmenty odbiorców z haseł",
    keyword_planner_enrichment: "Keyword Planner",
    negative_keyword_review_queue: "Akcje do sprawdzenia do wykluczeń",
    search_terms_review_queue: "Wyszukiwane hasła"
  };
  return titles[id] ?? fallback;
}

function adsOptimizerReadinessSummary(id: string, fallback: string) {
  const summaries: Record<string, string> = {
    ads_apply_safety_gate:
      "WILQ ma część podglądów do oceny, ale nie ma jeszcze bezpiecznej ścieżki zapisu zmian w Google Ads. Każdy zapis zmian pozostaje zablokowany.",
    budget_and_recommendation_review:
      "WILQ ma kontekst budżetów, rekomendacji albo udziału w wyświetleniach do ręcznej oceny. To nadal nie odblokowuje zmiany budżetu ani automatycznego przyjęcia rekomendacji.",
    campaign_review_queue:
      "WILQ łączy aktywność kampanii, KPI, budżety, rekomendacje i udział w wyświetleniach w kolejkę sprawdzania. To nie jest werdykt o zmarnowanym budżecie, CPA, ROAS ani opłacalności.",
    change_history_impact_review:
      "WILQ nie ma wystarczających zdarzeń historii zmian, żeby uczciwie ocenić wpływ zmian na wyniki kampanii.",
    custom_segments_review_queue:
      "WILQ ma akcji do sprawdzenia segmentów z haseł wyszukiwanych w Ads. To jest materiał do oceny, nie gotowe targetowanie.",
    keyword_planner_enrichment:
      "Keyword Planner nie zwrócił jeszcze danych wzbogacających, więc WILQ nie może pokazać prognozy ani rozmiaru odbiorców.",
    negative_keyword_review_queue:
      "WILQ ma terminy do ręcznej oceny jako potencjalne wykluczenia. To nie jest zgoda na zapis wykluczeń.",
    search_terms_review_queue:
      "WILQ ma wyszukiwane hasła do ręcznej oceny. Najpierw sprawdź koszt, intencję i konwersje, zanim powstanie jakakolwiek lista wykluczeń."
  };
  return summaries[id] ?? fallback;
}

function adsOptimizerReadinessNextStep(id: string, fallback: string) {
  const steps: Record<string, string> = {
    ads_apply_safety_gate:
      "Zostań w trybie oceny: sprawdź propozycje w WILQ, ale nie zapisuj zmian budżetów, rekomendacji, wykluczeń ani segmentów.",
    budget_and_recommendation_review:
      "Porównaj tempo wydawania, rekomendacje i udział w wyświetleniach przy kampaniach z kolejki. Zapis zmian pozostaje zablokowany.",
    campaign_review_queue:
      "Przejrzyj kampanie od góry kolejki. Najpierw sprawdź cel kampanii, jakość konwersji, budżet, wyszukiwane hasła i rekomendacje.",
    change_history_impact_review:
      "Potraktuj to jako checklistę gotowości: bez historii zmian i okien przed/po nie przypisuj wpływu zmian do wyników.",
    custom_segments_review_queue:
      "Przejrzyj hasła źródłowe i podgląd segmentów. Odrzuć nietrafione frazy i nie obiecuj zasięgu bez danych z Keyword Plannera.",
    keyword_planner_enrichment:
      "Zostaw segmenty w trybie oceny haseł źródłowych. Nie dopowiadaj prognoz ani rozmiaru odbiorców bez danych.",
    negative_keyword_review_queue:
      "Sprawdź intencję, dopasowanie i historię 90 dni. Zapis wykluczeń wymaga osobnego sprawdzenia w WILQ.",
    search_terms_review_queue:
      "Zacznij od haseł z największym kosztem. Nie nazywaj ich stratą budżetu bez oceny intencji i sprawdzenia w WILQ."
  };
  return steps[id] ?? fallback;
}

function adsDecisionSummary(decision: AdsDecisionItem) {
  const summaries: Partial<Record<AdsDecisionItem["decision_type"], string>> = {
    review_budget_context:
      "WILQ pokazuje koszt kampanii względem budżetu dziennego i ostatnich 7 dni. To jest kontekst do oceny, nie decyzja o skalowaniu.",
    review_business_context:
      "WILQ ma wstępny lokalny kontekst biznesowy: marżę, cel biznesowy i cel budżetu. Docelowy zwrot z reklam albo koszt pozyskania celu wymaga osobnego potwierdzenia.",
    review_campaign_activity:
      "WILQ pokazuje aktywność kampanii: kliknięcia, wyświetlenia, koszt, konwersje i wartość konwersji.",
    review_campaign_triage:
      "WILQ łączy kampanie, KPI, budżety, rekomendacje i udział w wyświetleniach w jedną kolejkę ręcznej oceny.",
    review_derived_kpi:
      "WILQ może policzyć KPI z bieżących faktów Ads, ale to nadal nie jest werdykt o opłacalności.",
    review_search_terms:
      "WILQ pokazuje wyszukiwane hasła do ręcznej oceny kosztu, intencji i konwersji."
  };
  return summaries[decision.decision_type] ?? decision.summary;
}

function adsStartHereSummary(decision: AdsDecisionItem, currencyCode?: string) {
  if (decision.decision_type === "review_campaign_triage") {
    const campaignCount = decision.campaign_triage_rows.length || decision.campaign_rows.length;
    return `${campaignCount} kampanii w kolejce oceny. Zacznij od celu, kosztu, konwersji, budżetu i haseł.`;
  }
  if (decision.decision_type === "review_campaign_activity") {
    const cost = adsCost(sumCampaignCostMicros(decision.campaign_rows), currencyCode);
    return `${decision.campaign_rows.length} kampanii z odczytem aktywności. Koszt w tej karcie: ${cost}.`;
  }
  if (decision.decision_type === "review_business_context") {
    return "Najpierw potwierdź marżę, cel biznesowy, docelowy koszt pozyskania celu i docelowy zwrot z reklam, zanim ktokolwiek nazwie wynik opłacalnym.";
  }
  if (decision.decision_type === "review_derived_kpi") {
    return `${decision.derived_kpi_rows.length} wierszy KPI do oceny. To nadal sygnał do sprawdzenia, nie werdykt CPA/ROAS.`;
  }
  if (decision.decision_type === "review_budget_context") {
    return `${decision.budget_rows.length} budżetów do sprawdzenia. Nie skaluj ani nie tnij budżetu bez sprawdzenia w WILQ.`;
  }
  if (decision.decision_type === "review_search_terms") {
    return `${decision.search_term_rows.length} haseł do oceny. Zacznij od kosztu i intencji, nie od automatycznego wykluczenia.`;
  }
  return adsDecisionSummary(decision);
}

function sumCampaignCostMicros(rows: AdsCampaignMetricRow[]) {
  return rows.reduce((total, row) => total + (row.cost_micros ?? 0), 0);
}

function adsDecisionRationale(decision: AdsDecisionItem) {
  const rationales: Partial<Record<AdsDecisionItem["decision_type"], string>> = {
    review_budget_context:
      "Budżet i koszt 7 dni pomagają ustalić, co sprawdzić najpierw. Bez historii zmian, udziału w wyświetleniach i zatwierdzonego celu biznesowego WILQ blokuje decyzje o budżecie.",
    review_business_context:
      "Ten kontekst pomaga czytać kampanie w realiach biznesu Ekologus, ale nie odblokowuje automatycznych wniosków o rentowności ani zmarnowanym budżecie.",
    review_campaign_activity:
      "To uczciwy pierwszy przegląd kampanii. Wnioski o CPA, ROAS, stracie budżetu i wykluczeniach wymagają dodatkowej oceny.",
    review_campaign_triage:
      "Kolejka mówi, od których kampanii zacząć. Nie zastępuje decyzji człowieka ani sprawdzenia w WILQ.",
    review_derived_kpi:
      "KPI są wyliczone z kosztu, konwersji i wartości konwersji w bieżącym evidence. Nie uwzględniają jeszcze pełnego modelu marży, targetów i historii zmian.",
    review_search_terms:
      "Hasła z ruchem lub kosztem są materiałem do oceny, ale WILQ nie nazywa ich automatycznie marnowaniem budżetu."
  };
  return rationales[decision.decision_type] ?? decision.rationale;
}

function adsDecisionNextStep(decision: AdsDecisionItem) {
  const steps: Partial<Record<AdsDecisionItem["decision_type"], string>> = {
    review_budget_context:
      "Użyj tego jako kontekstu przy ocenie kampanii. Nie skaluj budżetu bez sprawdzenia w WILQ.",
    review_business_context:
      "Użyj marży i celu budżetu jako kontekstu oceny kampanii. Docelowy zwrot z reklam albo koszt pozyskania celu zapisz dopiero po sprawdzeniu i zatwierdzeniu w WILQ.",
    review_campaign_activity:
      "Sprawdź kampanie z największym kosztem i ruchem. Decyzje budżetowe zostają za bramką sprawdzenia.",
    review_campaign_triage:
      "Przejrzyj kampanie od góry kolejki: cel, jakość konwersji, budżet, wyszukiwane hasła i rekomendacje.",
    review_derived_kpi:
      "Użyj KPI jako sygnału do kolejności oceny. Przed decyzją sprawdź marżę, tempo budżetu, historię zmian i rekomendacje.",
    review_search_terms:
      "Zacznij od haseł z największym kosztem. Wykluczenia przygotuj tylko po ocenie intencji, historii 90 dni i sprawdzenia w WILQ."
  };
  return steps[decision.decision_type] ?? decision.next_step;
}

function adsCondensedMeasurementPlan(decision: AdsDecisionItem | undefined) {
  if (!decision) {
    return "Po sprawdzenia w WILQ zapisz pre/post window check. Bez okna pomiarowego WILQ nie ocenia sukcesu ani porażki.";
  }
  if (decision.decision_type === "review_campaign_activity") {
    return "Po sprawdzeniu kampanii zapisz baseline kosztu, kliknięć, konwersji i wartości konwersji. Dopiero osobne okno pre/post oraz historia zmian pozwolą mówić o efekcie.";
  }
  if (decision.decision_type === "review_campaign_triage") {
    return "Po przejściu kolejki kampanii zapisz, które kampanie wymagają ręcznej decyzji. Efekt sprawdzimy dopiero przez pre/post window, historię zmian i ponowny odczyt Ads.";
  }
  if (decision.decision_type === "review_search_terms") {
    return "Po sprawdzeniu search terms zapisz akcji do sprawdzenia i blokady. Dopiero po potwierdzonej zmianie oraz pre/post window można oceniać wpływ na koszt, konwersje lub utratę ruchu.";
  }
  if (
    decision.decision_type === "review_negative_keyword_safety" ||
    decision.decision_type === "review_search_term_ngrams"
  ) {
    return "Po sprawdzeniu wykluczeń sprawdź zapytania, koszt i konwersje przed i po zmianie. Bez sprawdzenia efektu WILQ nie twierdzi, że oszczędzono budżet albo uniknięto utraty konwersji.";
  }
  if (decision.decision_type === "review_recommendations") {
    return "Po sprawdzeniu rekomendacji zapisz, które rekomendacje odrzucono albo skierowano do sprawdzenia. Efekt można ocenić dopiero po audycie zmiany i porównaniu metryk w kolejnym oknie.";
  }
  return "Po decyzji zapisz przegląd akcji, punkt odniesienia i sprawdzenie efektu. Brak okna pomiarowego oznacza brak twierdzenia o poprawie wyniku.";
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
  if (status === "missing_credentials") return "brakuje dostępu";
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
  if (sectionId === "ads_search_term_safety") return "Bezpieczeństwo 90 dni";
  if (sectionId === "ads_keyword_match_context") return "Kontekst słów kluczowych";
  if (sectionId === "ads_negative_keyword_safety") return "Ocena wykluczeń";
  if (sectionId === "ads_custom_segments") return "Segmenty niestandardowe";
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
    campaign_review_context: "kontekst oceny kampanii",
    budget_review_context: "kontekst oceny budżetu",
    human_strategy_review_context: "kontekst strategii człowieka",
    margin_context: "kontekst marży",
    business_goal_alignment: "dopasowanie do celu biznesowego",
    budget_goal_guardrail: "zasada bezpieczeństwa celu budżetu",
    target_roas_review: "ocena docelowego zwrotu z reklam",
    target_cpa_review: "ocena docelowego kosztu pozyskania celu",
    profitability_verdict: "ocena rentowności",
    target_kpi_verdict: "ocena KPI względem celu",
    budget_scaling: "skalowanie budżetu",
    budget_apply: "zmiana budżetu",
    recommendation_apply: "zapis rekomendacji",
    wasted_budget_claim: "wniosek o zmarnowanym budżecie",
    automatic_scaling: "automatyczne skalowanie",
    profitability_verdict_without_value_model_review:
      "ocena rentowności bez przeglądu modelu wartości"
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
    target_roas: "docelowy zwrot z reklam",
    target_cpa_micros: "docelowy koszt pozyskania celu",
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
    keyword_text: "słowo kluczowe",
    keyword_match_type: "typ dopasowania słowa",
    criterion_status: "status słowa",
    keyword_negative: "wykluczające słowo",
    campaign: "kampania",
    ad_group: "grupa reklam",
    status: "status zapytania"
  };
  return labels[value] ?? value;
}

function adsOptimizerReadinessItemLabel(value: string) {
  const labels: Record<string, string> = {
    campaign_review_queue: "kampanie do oceny",
    budget_and_recommendation_review: "budżety i rekomendacje",
    search_terms_review_queue: "wyszukiwane hasła",
    negative_keyword_review_queue: "wykluczenia do oceny",
    custom_segments_review_queue: "segmenty niestandardowe",
    keyword_planner_enrichment: "Keyword Planner",
    change_history_impact_review: "historia zmian",
    ads_apply_safety_gate: "bramka zapisu zmian"
  };
  return labels[value] ?? value;
}

function adsStrategyReviewStatusLabel(value: string) {
  const labels: Record<string, string> = {
    missing: "brak oceny",
    approved_for_prepare: "zatwierdzone do przygotowania",
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

function adsCampaignReviewReason(row: AdsCampaignMetricRow, currencyCode?: string) {
  const parts = [
    `${adsNumber(row.clicks)} kliknięć`,
    `${adsNumber(row.impressions)} wyświetleń`,
    `${adsCost(row.cost_micros, currencyCode)} kosztu`,
    `${adsNumber(row.conversions)} konwersji`
  ];
  return `Kampania do oceny na podstawie bieżącego odczytu: ${parts.join(
    ", "
  )}. Nie jest to werdykt CPA, ROAS ani opłacalności.`;
}

function adsCampaignTriageReason(row: AdsCampaignTriageRow, currencyCode?: string) {
  const facts = [
    `${adsCost(row.cost_micros, currencyCode)} kosztu`,
    `${adsNumber(row.clicks)} kliknięć`,
    `${adsNumber(row.conversions)} konwersji`,
    row.advertising_channel_type ? `kanał ${row.advertising_channel_type}` : null
  ].filter(Boolean);
  return `WILQ ustawia tę kampanię w kolejce oceny na podstawie faktów: ${facts.join(
    ", "
  )}. To nie jest werdykt o zmarnowanym budżecie, CPA, ROAS ani opłacalności.`;
}

function adsCampaignTriageNextStep(row: AdsCampaignTriageRow) {
  const gates = row.human_review_gate_labels.slice(0, 3);
  return `Sprawdź kampanię ręcznie: ${gates.join(
    ", "
  ) || "cel kampanii, konwersje, budżet i wyszukiwane hasła"}. Zapis zmian wymaga sprawdzenia w WILQ i potwierdzenia człowieka.`;
}

function adsRecommendationReviewReason(row: AdsRecommendationRow, currencyCode?: string) {
  if (!row.impact_available) {
    return "Google Ads zwrócił rekomendację bez metryk wpływu. WILQ może ją pokazać tylko do ręcznej oceny, bez obietnicy poprawy wyniku.";
  }
  const facts = [
    `zmiana kliknięć ${adsSignedNumber(row.delta_clicks)}`,
    `zmiana wyświetleń ${adsSignedNumber(row.delta_impressions)}`,
    `zmiana kosztu ${adsSignedCost(row.delta_cost_micros, currencyCode)}`,
    `zmiana konwersji ${adsSignedNumber(row.delta_conversions)}`
  ];
  return `Rekomendacja do ręcznej oceny: ${facts.join(
    ", "
  )}. WILQ nie przyjmuje jej automatycznie i nie twierdzi, że poprawi wynik kampanii.`;
}

function adsNegativeKeywordReason(
  candidate: AdsNegativeKeywordCandidate,
  currencyCode?: string
) {
  const facts = [
    `${adsNumber(candidate.clicks)} kliknięć`,
    `${adsCost(candidate.cost_micros, currencyCode)} kosztu`,
    `${adsNumber(candidate.conversions)} konwersji`,
    `${adsNumber(candidate.clicks_90d)} kliknięć w 90 dni`
  ];
  return `Termin do ręcznej oceny jako potencjalne wykluczenie: ${facts.join(
    ", "
  )}. To nie jest gotowa lista wykluczeń ani dowód marnowania budżetu.`;
}

function adsNegativeKeywordNextStep(candidate: AdsNegativeKeywordCandidate) {
  const gates = candidate.human_review_gate_labels.slice(0, 3);
  return `Przed zapisem zmian sprawdź: ${gates.join(
    ", "
  ) || "intencję, dopasowanie i historię 90 dni"}. Wykluczenie wymaga sprawdzenia w WILQ.`;
}

function adsNegativeKeywordPayloadReason(reason: string) {
  if (reason.includes("90-day") || reason.includes("90_day")) {
    return "wymagana 90-dniowa kontrola bezpieczeństwa i ręczna ocena";
  }
  if (reason.includes("human")) return "wymagana ręczna ocena";
  if (reason.includes("validation")) return "wymagane sprawdzenie w WILQ";
  return reason;
}

function adsGoogleOperationLabel(value: string) {
  const labels: Record<string, string> = {
    apply_recommendation: "zapis rekomendacji",
    campaign_budget_update: "zmiana budżetu kampanii",
    create_negative_keyword: "dodanie wykluczenia",
    create_custom_segment: "utworzenie segmentu"
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
