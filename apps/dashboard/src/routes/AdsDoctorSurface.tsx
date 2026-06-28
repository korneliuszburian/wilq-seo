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
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { ActionObjectFocus } from "./ActionObjectPanels";
import {
  AdsCustomSegmentAudienceForecastPanel,
  AdsCustomSegmentCandidatesPanel
} from "./CustomSegmentsDiagnosticSurface";
import { ActionPreviewCard } from "../components/ActionPreviewCard";

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
              {data.connector.label}: {data.connector_status_label}
              <span className="sr-only">; </span>
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_status_label}
              <span className="sr-only">; </span>
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {data.latest_refresh_status_label}
                <span className="sr-only">; </span>
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
        <AdsBlockedHandoffPanel handoff={data.blocked_handoff} />
      ) : null}

      <AdsCondensedDecisionPanel data={data} currencyCode={currencyCode} connectorStatuses={connectorStatuses} />
      <AdsMarketSnapshot data={data} currencyCode={currencyCode} />
      <AdsExpandableReviewPanel data={data} currencyCode={currencyCode} connectorStatuses={connectorStatuses} />

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
            WILQ ma {actionSummaryLabel} dla Google Ads. Otwórz je dopiero wtedy, gdy
            chcesz zapisać przegląd człowieka, wygenerować podgląd zmian albo
            sprawdzić techniczne warunki akcji.
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
    ? primaryDecision.blocked_claim_labels
    : summary.blocked_claim_labels;
  const missingInputs = primaryDecision
    ? primaryDecision.missing_read_contract_labels
    : summary.missing_read_contract_labels;
  const evidenceSummary = primaryDecision
    ? primaryDecision.evidence_summary_label
    : summary.evidence_summary_label;
  const actionSummary = primaryDecision?.action_summary_label ?? summary.action_summary_label;
  const sourceConnectors = primaryDecision
    ? primaryDecision.source_connector_labels
    : summary.source_connector_labels;

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
            <TraceLine label="Źródła" values={sourceConnectors} />
            <TraceLine
              label="Stan danych"
              values={[
                data.live_data_status_label,
                data.latest_refresh
                  ? `ostatni odczyt: ${data.latest_refresh_status_label}`
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
          values={summary.missing_read_contract_labels}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={summary.blocked_claim_labels.slice(0, 8)}
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
  const allowedMetrics = summary.allowed_metric_labels;
  const missingReadContracts = summary.missing_read_contract_labels;
  const operatorReviewGates = summary.operator_review_gate_labels;
  const blockedClaims = summary.blocked_claim_labels;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd Google Ads
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">{summary.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ porządkuje bieżący odczyt Ads w kolejkę decyzji: kampanie,
            wyszukiwane hasła, wskaźniki, budżety i rekomendacje. To jest przegląd
            oparty o dowody, bez zapisu zmian i bez oceny opłacalności.
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
            label="Rekomendacje"
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
      <AdsStartHerePanel decisions={decisions.slice(0, 3)} />

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
            <TraceLine label="Brakujące dane" values={missingReadContracts} empty="brak" />
            <TraceLine label="Wymagana ocena" values={operatorReviewGates} empty="brak" />
            <TraceLine
              label="Dowody"
              values={[summary.evidence_summary_label]}
              empty="brak"
            />
            <TraceLine
              label="Akcje do sprawdzenia"
              values={[summary.action_summary_label]}
              empty="brak"
            />
            <TraceLine label="Nie wolno twierdzić" values={blockedClaims} empty="brak" />
          </div>
        </div>
      </div>
    </section>
  );
}

function AdsStartHerePanel({ decisions }: { decisions: AdsDecisionItem[] }) {
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
                  Krok {index + 1}: {decision.title}
                </div>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {decision.decision_type_label} / {decision.status_label}
                </p>
              </div>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">
              {decision.start_here_summary}
            </p>
            <p className="mt-2 text-xs font-medium leading-5 text-ink">
              {decision.next_step}
            </p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Akcje"
                values={[decision.action_summary_label]}
                empty="brak"
              />
              <TraceLine
                label="Nie wolno"
                values={decision.blocked_claim_labels.slice(0, 3)}
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
          <MetricTile label="Tryb" value={contract.mode_label} />
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
          empty="Brak aktywnych blokad."
        />
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Brakujące dane"
          values={contract.missing_read_contract_labels}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={contract.blocked_claim_labels}
          empty="brak"
        />
        <TraceLine
          label="Dowody"
          values={[contract.evidence_summary_label]}
          empty="brak"
        />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[contract.action_summary_label]}
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
                  {item.label}
                </h4>
                <p className="mt-1 text-xs text-slate-500">
                  {item.title}
                </p>
              </div>
              <span className="rounded-md border border-line bg-slate-50 px-2 py-1 text-xs text-slate-600">
                {item.status_label} / {item.risk_label}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-700">
              {item.summary}
            </p>
            <p className="mt-2 text-xs font-medium text-ink">
              {item.next_step}
            </p>
            <div className="mt-2 grid gap-1 text-xs text-slate-600">
              <TraceLine
                label="Warunki źródłowe"
                values={[item.source_contract_summary_label]}
                empty="brak"
              />
              <TraceLine
                label="Braki"
                values={item.missing_read_contract_labels}
                empty="brak"
              />
              <TraceLine
                label="Blokady"
                values={item.blocked_claim_labels}
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
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {decision.decision_type_label} / {decision.status_label}
          </p>
        </div>
        <span className="rounded-md border border-line bg-white px-2 py-1 text-xs text-slate-600">
          ryzyko: {decision.risk_label}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">
        {decision.summary}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-600">
        {decision.rationale}
      </p>
      <p className="mt-2 text-sm font-medium text-ink">
        {decision.next_step}
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
          values={[decision.evidence_summary_label]}
          empty="brak"
        />
        <TraceLine label="Źródła" values={decision.source_connector_labels} />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[decision.action_summary_label]}
          empty="brak"
        />
        {decision.operator_review_gate_labels.length > 0 ? (
          <TraceLine
            label="Wymagana ocena"
            values={decision.operator_review_gate_labels}
          />
        ) : null}
        <TraceLine label="Nie wolno twierdzić" values={decision.blocked_claim_labels} />
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
  const missingReadContracts = summary.missing_read_contract_labels;
  const operatorReviewGates = summary.operator_review_gate_labels;
  const blockedClaims = summary.blocked_claim_labels;

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
          <MetricTile label="Waluta" value={currencyCode ?? "brak"} />
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
        <TraceLine label="Brakujące dane" values={missingReadContracts} />
        <TraceLine label="Wymaga oceny" values={operatorReviewGates} empty="brak" />
        <TraceLine label="Nie wolno twierdzić" values={blockedClaims} />
        <LinkedTraceLine label="Dowody" values={data.evidence_ids.slice(0, 8)} kind="evidence" />
        <TraceLine
          label="Sekcje źródłowe"
          values={data.sections.map((section) => section.title)}
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
          {interpretation.status_label}
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Wolno użyć jako"
          values={interpretation.allowed_use_labels}
          empty="brak"
        />
        <TraceLine
          label="Zablokowane użycia"
          values={interpretation.blocked_use_labels}
          empty="brak"
        />
        <TraceLine
          label="Braki"
          values={interpretation.missing_requirement_labels}
          empty="brak"
        />
        <TraceLine
          label="Polityki"
          values={[interpretation.policy_summary_label]}
          empty="brak"
        />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[interpretation.action_summary_label]}
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
            {strategyReadiness.status_label} / {strategyReadiness.latest_review_status_label}
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
          <MetricTile label="Braki" value={strategyReadiness.missing_read_contract_summary_label} />
          <MetricTile label="Ocena" value={strategyReadiness.latest_review_status_label} />
        </div>
        <p className="mt-3 text-xs font-medium text-ink">{strategyReadiness.next_step}</p>
        <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
          <TraceLine
            label="Wymagane sprawdzenie"
            values={[strategyReadiness.required_validation_summary_label]}
            empty="brak"
          />
          <TraceLine
            label="Braki"
            values={strategyReadiness.missing_read_contract_labels}
            empty="brak"
          />
          <TraceLine
            label="Nie wolno twierdzić"
            values={strategyReadiness.blocked_claim_labels}
            empty="brak"
          />
          <TraceLine
            label="Akcje do sprawdzenia"
            values={[strategyReadiness.action_summary_label]}
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
      <BlockerNotice message="Brak szczegółowych wierszy kampanii. WILQ nie może analizować kampanii bez odczytu Google Ads." />
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
            <th className="py-2 pr-4 font-semibold">Wartość konwersji</th>
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
                {row.review_reason}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
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
      <BlockerNotice message="Brak kolejki oceny kampanii. WILQ potrzebuje aktywności kampanii, wskaźników, budżetu i zasad oceny, żeby ustalić kolejność sprawdzania." />
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
              "Ranking kampanii do ręcznej oceny. To nie jest ocena zmarnowanego budżetu, kosztu pozyskania celu, zwrotu z reklam ani opłacalności."}
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
                  {row.advertising_channel_type_label ?? "kanał: brak"} /{" "}
                  {row.campaign_status_label ?? "status: brak"} / {row.target_status_label}
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
              <MetricTile label="Zwrot z reklam" value={adsNumber(row.roas)} />
              <MetricTile
                label="Wydanie 7d"
                value={adsPercent(row.spend_to_budget_ratio_7d)}
              />
            </div>

            <p className="mt-3 text-xs leading-5 text-slate-700">
              {row.review_reason}
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
                values={row.missing_read_contract_labels}
                empty="brak"
              />
              <TraceLine
                label="Dowody"
                values={[row.evidence_summary_label]}
                empty="brak"
              />
              <TraceLine
                label="Akcje do sprawdzenia"
                values={[row.action_summary_label]}
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
      <BlockerNotice message="Brak wyliczalnych wskaźników kampanii. WILQ potrzebuje kosztu, kliknięć, konwersji i wartości konwersji w danych kampanii." />
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
            <th className="py-2 pr-4 font-semibold">Koszt pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">Docelowy koszt pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">Różnica kosztu pozyskania celu</th>
            <th className="py-2 pr-4 font-semibold">zwrot z reklam</th>
            <th className="py-2 pr-4 font-semibold">Docelowy zwrot z reklam</th>
            <th className="py-2 pr-4 font-semibold">Różnica zwrot z reklam</th>
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
                {row.blocked_claim_labels.slice(0, 2).join(", ")}
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
  currencyCode,
  emptyStateMessage
}: {
  rows: AdsBudgetPacingRow[];
  currencyCode?: string;
  emptyStateMessage?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice
        message={
          emptyStateMessage ||
          "Brak kontekstu budżetu kampanii. Odśwież dane Google Ads z polami budżetu, żeby pokazać koszt względem budżetu dziennego."
        }
      />
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
                  {row.advertising_channel_type_label} / {row.budget_period_label}
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
                {row.preview_card ? (
                  <div className="min-w-72">
                    <ActionPreviewCard card={row.preview_card} />
                  </div>
                ) : (
                  "brak"
                )}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.blocked_claim_labels.slice(0, 2).join(", ")}
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
                  ID budżetu: {row.budget_id ?? "brak"} / kampanie: {row.campaign_count}
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
                        {share.advertising_channel_type_label} / {share.campaign_status_label}
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
                values={row.blocked_claim_labels}
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
                  {row.recommendation_type_label}
                </div>
                <div className="mt-1 text-xs leading-5 text-slate-600">
                  Zakres: {row.campaign_count ?? 0} kampanii. Szczegóły techniczne
                  powiązania są dostępne w danych akcji.
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
              values={row.blocked_claim_labels}
            />
            <LinkedTraceLine
              label="Dowody"
              values={row.evidence_ids.slice(0, 2)}
              kind="evidence"
            />
            {row.preview_card ? (
              <div className="mt-3">
                <ActionPreviewCard card={row.preview_card} />
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
}

function AdsImpressionShareRowsTable({
  rows,
  emptyStateMessage
}: {
  rows: AdsImpressionShareRow[];
  emptyStateMessage?: string;
}) {
  if (rows.length === 0) {
    return (
      <BlockerNotice
        message={
          emptyStateMessage ||
          "Brak wierszy udziału w wyświetleniach. Odśwież dane Google Ads z metrykami udziału w wyświetleniach, żeby ocenić utraconą ekspozycję."
        }
      />
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-line">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-line bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
          <tr>
            <th className="py-2 pl-3 pr-4 font-semibold">Kampania</th>
            <th className="py-2 pr-4 font-semibold">Udział w wyświetleniach</th>
            <th className="py-2 pr-4 font-semibold">Utrata przez budżet</th>
            <th className="py-2 pr-4 font-semibold">Utrata przez ranking</th>
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
                {row.blocked_claim_labels.slice(0, 2).join(", ")}
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
      <BlockerNotice message="Brak wierszy historii zmian. WILQ nie może łączyć skuteczności ze zmianami kampanii bez odczytu historii zmian." />
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
                {row.change_resource_label || "zasób zmiany do sprawdzenia"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.resource_change_operation_label || "operacja: brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.client_type_label || "źródło zmiany: brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_label || "brak kampanii w odczycie"}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.changed_field_labels.length > 0
                  ? row.changed_field_labels.slice(0, 4).join(", ")
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
          <MetricTile label="Status" value={contract.status_label} />
        </div>
      </div>

      {rows.length === 0 ? (
        <BlockerNotice message="Brak zdarzeń historii zmian do oceny wpływu. WILQ może pokazać tylko blokadę, nie ocenę wpływu zmian." />
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
          values={contract.allowed_metric_labels}
          empty="brak"
        />
        <TraceLine
          label="Brakujące dane"
          values={contract.missing_read_contract_labels}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={contract.blocked_claim_labels}
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
            {row.campaign_label || "brak kampanii w odczycie"}
          </h4>
          <p className="mt-1 text-xs text-slate-500">
            {row.change_event_label || "brak identyfikatora zmiany w odczycie"} /{" "}
            {row.change_date_time ?? "brak daty"}
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
        <MetricTile label="Wartość konwersji" value={adsNumber(row.current_conversion_value)} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine
          label="Zmienione pola"
          values={row.changed_field_labels}
          empty="brak pól"
        />
        <TraceLine
          label="Braki"
          values={row.missing_read_contract_labels}
          empty="brak"
        />
        <TraceLine
          label="Blokady"
          values={row.blocked_claim_labels}
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
                      {row.campaign_label || "brak kampanii w odczycie"}
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
                  {row.campaign_label || "brak kampanii w odczycie"} / koszt{" "}
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
          values={contract.blocked_claim_labels}
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
      <BlockerNotice message="Brak szczegółowych wierszy zapytań. WILQ nie może analizować zapytań ani strat budżetu bez danych o wyszukiwanych hasłach." />
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
                {row.campaign_label || "brak kampanii w odczycie"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_label || "brak grupy reklam w odczycie"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
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
            <th className="py-2 pr-4 font-semibold">Źródłowe zapytania</th>
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
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
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
                {row.campaign_label || "brak kampanii w odczycie"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_label || "brak grupy reklam w odczycie"}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.clicks_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.impressions_90d)}</td>
              <td className="py-2 pr-4 text-slate-700">
                {adsCost(row.cost_micros_90d, currencyCode)}
              </td>
              <td className="py-2 pr-4 text-slate-700">{adsNumber(row.conversions_90d)}</td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
              </td>
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
      <BlockerNotice message="Brak kontekstu istniejących słów kluczowych i typów dopasowania. WILQ nie powinien zdejmować blokady z oceny wykluczeń bez odczytu istniejących słów kluczowych i wykluczeń w grupach reklam." />
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
              <td className="py-2 pr-4 text-slate-700">
                {row.match_type_label || "typ dopasowania: brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.negative_label || row.criterion_status_label || "status: brak"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.campaign_label || "brak kampanii w odczycie"}
              </td>
              <td className="py-2 pr-4 text-slate-700">
                {row.ad_group_label || "brak grupy reklam w odczycie"}
              </td>
              <td className="py-2 pr-3 text-xs text-slate-600">
                {row.evidence_summary_label}
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
                  {candidate.campaign_label || "brak kampanii w odczycie"} /{" "}
                  {candidate.ad_group_label || "brak grupy reklam w odczycie"}
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
              Bezpieczeństwo: {candidate.safety_status_label || "brak statusu"}
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
              {candidate.next_step}
            </p>
            {candidate.preview_card ? (
              <div className="mt-2">
                <ActionPreviewCard card={candidate.preview_card} />
              </div>
            ) : null}
            {candidate.keyword_context_rows.length > 0 ? (
              <div className="mt-2 rounded-md border border-line bg-slate-50 p-2 text-xs leading-5 text-slate-700">
                <div className="font-semibold uppercase tracking-normal text-slate-600">
                  Istniejące słowa kluczowe w tej grupie
                </div>
                {candidate.keyword_context_rows.slice(0, 4).map((row) => (
                  <div key={`${row.criterion_id ?? row.keyword_text}-${row.match_type}`}>
                    {row.keyword_text} / {row.match_type_label}
                    {row.negative_label ? ` / ${row.negative_label}` : ""}
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
              <TraceLine label="Wymagane kontrole" values={candidate.required_check_labels} />
              <LinkedTraceLine
                label="Dowody"
                values={uniqueValues([
                  ...candidate.evidence_ids,
                  ...candidate.safety_evidence_ids
                ]).slice(0, 3)}
                kind="evidence"
              />
              <TraceLine label="Nie wolno twierdzić" values={candidate.blocked_claim_labels} />
            </div>
          </article>
        ))}
      </div>
    </div>
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
          empty="brak"
        />
        <TraceLine label="Nie wolno twierdzić" values={handoff.blocked_claim_labels} />
      </div>
    </section>
  );
}

function adsStrategyContextValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "brak";
  if (typeof value === "number") return adsNumber(value);
  return String(value);
}

function adsCampaignTriageNextStep(row: AdsCampaignTriageRow) {
  const gates = row.human_review_gate_labels.slice(0, 3);
  return `Sprawdź kampanię ręcznie: ${gates.join(
    ", "
  ) || "cel kampanii, konwersje, budżet i wyszukiwane hasła"}. Zapis zmian wymaga sprawdzenia w WILQ i potwierdzenia człowieka.`;
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
