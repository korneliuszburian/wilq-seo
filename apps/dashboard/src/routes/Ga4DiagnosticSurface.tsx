import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import {
  getActions,
  getGa4Diagnostics,
  type ActionObject,
  type ActionPreviewCardViewModel,
  type Ga4DiagnosticsResponse
} from "../lib/api";
import { DiagnosticPage } from "../components/DiagnosticSurfaceShell";
import { BlockerNotice, LoadingBand, MetricTile, PlainChipRow } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { Ga4OperatorSummary } from "./Ga4Sections/OperatorSummarySection";
import {
  Ga4ExpandableActionsPanel,
  Ga4ExpandableReviewPanel
} from "./Ga4Sections/ReviewActionsSection";
import type { Ga4DecisionItem, Ga4MetricFact } from "./Ga4Sections/Shared";

export function Ga4DiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ga4-diagnostics"],
    queryFn: getGa4Diagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  return (
    <DiagnosticPage
      query={diagnostics}
      title="GA4"
      description="Dedykowany widok GA4 z WILQ. Pokazuje jakość ruchu ze stron wejścia, dopasowanie WordPress i problemy pomiaru bez udawania konwersji, zwrot z reklam albo przychód."
      unavailableMessage="Nie udało się odczytać danych GA4. Ten widok nie może udawać jakości ruchu ani konwersji bez WILQ."
      metrics={(data) => (
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Grupy ruchu" value={data.landing_group_count} />
          <MetricTile label="Problemy pomiaru" value={data.operator_summary.measurement_issue_count} />
          <MetricTile label="Brak WP" value={data.operator_summary.wordpress_missing_count} />
          <MetricTile label="Blokady decyzji" value={data.decision_blocker_count} />
        </div>
      )}
    >
      {(data) => <Ga4DiagnosticBody data={data} actions={actions} />}
    </DiagnosticPage>
  );
}

function Ga4DiagnosticBody({
  data,
  actions
}: {
  data: Ga4DiagnosticsResponse;
  actions: UseQueryResult<ActionObject[]>;
}) {
  if (actions.isLoading) return <LoadingBand />;
  if (actions.error || !actions.data) {
    return (
      <BlockerNotice message="Nie udało się pobrać akcji do sprawdzenia. Odśwież widok albo sprawdź status WILQ." />
    );
  }

  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const trackingPreviewCards = ga4TrackingQualityPreviewCardsFromActions(routeActions);
  const latestRefresh = data.latest_refresh;

  return (
    <>
      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status GA4: pomiar i jakość ruchu
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {data.freshness_assessment.summary}
            </p>
            <p className="mt-1 text-sm font-medium text-ink">
              {data.freshness_assessment.next_step}
            </p>
          </div>
          <PlainChipRow
            values={[
              `${data.connector.label}: ${data.connector_status_label}`,
              data.freshness_assessment.state_label,
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

      <Ga4OperatorSummary
        data={data}
        DecisionCard={Ga4DecisionCard}
        MeasurementIssueCard={Ga4MeasurementIssueCard}
      />

      <Ga4ExpandableReviewPanel
        data={data}
        trackingPreviewCards={trackingPreviewCards}
        DecisionCard={Ga4DecisionCard}
        DiagnosticProof={Ga4DiagnosticProof}
      />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <Ga4ExpandableActionsPanel
            actions={routeActions}
            actionSummaryLabel={data.action_summary_label}
          />
        </div>
      ) : null}
    </>
  );
}

function Ga4MeasurementIssueCard({
  decision
}: {
  decision: Ga4DecisionItem;
}) {
  return (
    <article className="rounded-md border border-line bg-white p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-ink">{decision.title}</h4>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {decision.decision_type_label}
          </p>
        </div>
        <StatusBadge value={decision.status} label={decision.status_label} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.next_step}</p>
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.landing_page_label ? (
          <span className="rounded border border-line bg-slate-50 px-2 py-1">
            Strona wejścia: {decision.landing_page_label}
          </span>
        ) : null}
        {decision.source_medium_label ? (
          <span className="rounded border border-line bg-slate-50 px-2 py-1">
            Źródło: {decision.source_medium_label}
          </span>
        ) : null}
        {decision.campaign_name_label ? (
          <span className="rounded border border-line bg-slate-50 px-2 py-1">
            Kampania: {decision.campaign_name_label}
          </span>
        ) : null}
      </div>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-3 text-xs text-slate-600">
        <TraceLine
          label="Dowód"
          values={[decision.evidence_summary_label]}
          empty="WILQ nie podał dowodu źródłowego; nie traktuj tej luki jako potwierdzonej diagnozy."
        />
      </div>
    </article>
  );
}

function Ga4DecisionCard({
  decision
}: {
  decision: Ga4DecisionItem;
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {decision.decision_type_label}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge value={decision.status} label={decision.status_label} />
          <StatusBadge value={decision.risk} label={decision.risk_label} />
        </div>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.rationale}</p>
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.landing_page ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Strona wejścia: {decision.landing_page_label || decision.landing_page}
          </span>
        ) : null}
        {decision.source_medium ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Źródło: {decision.source_medium_label || decision.source_medium}
          </span>
        ) : null}
        {decision.campaign_name ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kampania: {decision.campaign_name_label || decision.campaign_name}
          </span>
        ) : null}
        {decision.wordpress_match ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            WordPress: {decision.wordpress_match_label}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {decision.wordpress_match_confidence_label}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Dowody w WILQ"
          values={decision.evidence_summary_label ? [decision.evidence_summary_label] : []}
          empty="WILQ nie podał dowodów źródłowych; nie traktuj decyzji jako rekomendacji."
        />
        <TraceLine
          label="Źródła"
          values={decision.source_connector_labels}
          empty="WILQ nie podał źródeł danych; nie oceniaj pomiaru bez źródła."
        />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[decision.action_summary_label]}
        />
        <TraceLine label="Nie wolno twierdzić" values={decision.blocked_claim_labels} />
      </div>
    </article>
  );
}

function ga4TrackingQualityPreviewCardsFromActions(
  actions: ActionObject[]
): ActionPreviewCardViewModel[] {
  return actions.flatMap((action) => {
    return action.preview_cards.filter((card) => card.kind === "ga4_tracking_quality_review");
  });
}

function Ga4DiagnosticProof({
  data
}: {
  data: Ga4DiagnosticsResponse;
}) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i warunki pomiaru GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót źródeł i blokad w WILQ. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Obszary danych" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Dowody" value={data.evidence_summary_label} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? <Ga4MetricTiles facts={visibleMetricFacts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => section.label)} />
        <TraceLine label="Dowody" values={[data.evidence_summary_label]} />
        <TraceLine
          label="Źródła"
          values={data.source_connector_labels}
          empty="WILQ nie podał źródeł danych; ten panel nie uzasadnia oceny pomiaru."
        />
        <TraceLine label="Akcje" values={[data.action_summary_label]} />
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
      </div>
    </section>
  );
}

function Ga4MetricTiles({ facts }: { facts: Ga4MetricFact[] }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
      {facts.map((fact, index) => (
        <MetricTile
          key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
          label={fact.metric_label || "metryka GA4 bez etykiety"}
          value={formatGa4MetricValue(fact.value)}
        />
      ))}
    </div>
  );
}

function formatGa4MetricValue(value: string | number | boolean) {
  if (typeof value === "boolean") return value ? "tak" : "nie";
  return value;
}
