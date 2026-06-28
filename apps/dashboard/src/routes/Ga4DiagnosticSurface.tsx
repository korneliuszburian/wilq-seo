import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ShieldAlert } from "lucide-react";

import {
  ActionObject,
  ActionPreviewCardViewModel,
  ConnectorStatus,
  Ga4DiagnosticsResponse,
  getActions,
  getConnectors,
  getGa4Diagnostics
} from "../lib/api";
import { ActionPreviewCard } from "../components/ActionPreviewCard";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { TraceLine } from "../components/TraceLine";
import { ActionObjectFocus } from "./ActionObjectPanels";

type Ga4DecisionItem = Ga4DiagnosticsResponse["decision_queue"][number];
type Ga4MetricFact = Ga4DiagnosticsResponse["sections"][number]["metric_facts"][number];

export function Ga4DiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["ga4-diagnostics"],
    queryFn: getGa4Diagnostics
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
        <BlockerNotice message="Nie udało się odczytać danych GA4. Ten widok nie może udawać jakości ruchu ani konwersji bez WILQ." />
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
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const trackingPreviewCards = ga4TrackingQualityPreviewCardsFromActions(routeActions);
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">GA4</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok GA4 z WILQ. Pokazuje jakość ruchu ze stron wejścia,
            dopasowanie WordPress i problemy pomiaru bez udawania konwersji, zwrot z reklam
            albo przychód.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Grupy ruchu" value={data.landing_group_count} />
          <MetricTile label="Problemy pomiaru" value={data.operator_summary.measurement_issue_count} />
          <MetricTile label="Brak WP" value={data.operator_summary.wordpress_missing_count} />
          <MetricTile label="Blokady decyzji" value={data.decision_blocker_count} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status GA4 / pomiar i jakość ruchu
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">{data.strict_instruction}</p>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {data.freshness_assessment.summary}
            </p>
            <p className="mt-1 text-sm font-medium text-ink">
              {data.freshness_assessment.next_step}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.connector.label}: {data.connector_status_label}
              <span className="sr-only">; </span>
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.freshness_assessment.state_label}
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

      <Ga4OperatorSummary data={data} connectorStatuses={connectorStatuses} />

      <Ga4ExpandableReviewPanel
        data={data}
        trackingPreviewCards={trackingPreviewCards}
        connectorStatuses={connectorStatuses}
      />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <Ga4ExpandableActionsPanel actions={routeActions} />
        </div>
      ) : null}
    </main>
  );
}

function Ga4ExpandableReviewPanel({
  data,
  trackingPreviewCards,
  connectorStatuses
}: {
  data: Ga4DiagnosticsResponse;
  trackingPreviewCards: ActionPreviewCardViewModel[];
  connectorStatuses: ConnectorStatus[];
}) {
  const [showReview, setShowReview] = useState(false);

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Pełny przegląd GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Pierwszy ekran pokazuje status pomiaru i najważniejszą decyzję. Rozwiń
            pełny przegląd, gdy chcesz zobaczyć problemy pomiaru, dowody, podgląd
            przeglądu i bramę bezpieczeństwa GA4.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Pomiar" value={data.operator_summary.measurement_issue_count} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
          <MetricTile label="Podglądy" value={trackingPreviewCards.length} />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowReview((current) => !current)}
        className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:bg-slate-50"
      >
        {showReview ? "Ukryj pełny przegląd GA4" : "Pokaż pełny przegląd GA4"}
      </button>

      {showReview ? (
        <div className="mt-4 grid gap-6">
          <Ga4MeasurementIssues data={data} connectorStatuses={connectorStatuses} />
          <Ga4DiagnosticProof data={data} />
          {trackingPreviewCards.length > 0 ? (
            <section className="rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                Podgląd przeglądu GA4
              </h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                Kolejka akcji do sprawdzenia. Pokazuje stronę wejścia, źródło
                ruchu i kampanię do kontroli bez zapisu zmian w GA4.
              </p>
            </div>
            <MetricTile label="Pozycje" value={trackingPreviewCards.length} />
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            {trackingPreviewCards.slice(0, 4).map((card) => (
              <ActionPreviewCard key={card.id} card={card} />
            ))}
          </div>
            </section>
          ) : null}

          <section className="rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa GA4
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować ocenę jakości ruchu i checklistę pomiaru, ale
              nie może uznać wyniku za problem kampanii bez konwersji, kosztów i
              sprawdzenia w WILQ.
            </p>
          </div>
        </div>
        <TraceLine
          label="Nie wolno twierdzić"
          values={data.sections.flatMap((section) => section.blocked_claim_labels)}
        />
          </section>
        </div>
      ) : null}
    </section>
  );
}

function Ga4ExpandableActionsPanel({ actions }: { actions: ActionObject[] }) {
  const [showActions, setShowActions] = useState(false);
  const actionCountLabel = formatGa4ActionCount(actions.length);
  const actionCountSentence =
    actions.length === 1 ? "WILQ ma jedną akcję dla GA4." : `WILQ ma ${actionCountLabel} dla GA4.`;

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {actionCountSentence} Otwórz ją dopiero wtedy, gdy
            chcesz zapisać przegląd człowieka, wygenerować podgląd zmian albo
            sprawdzić warunki bezpiecznego zapisu.
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

function Ga4MeasurementIssues({
  data,
  connectorStatuses
}: {
  data: Ga4DiagnosticsResponse;
  connectorStatuses: ConnectorStatus[];
}) {
  const measurementDecisions = data.decision_queue.filter(
    (decision) => decision.decision_type === "fix_measurement"
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Problemy pomiaru GA4
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Braki w wymiarach raportu są problemem pomiaru lub
            atrybucji. WILQ pokazuje je osobno, żeby nie mieszać ich z oceną
            jakości strony wejścia albo kampanii.
          </p>
        </div>
        <MetricTile label="Do kontroli" value={measurementDecisions.length} />
      </div>
      {measurementDecisions.length > 0 ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {measurementDecisions.slice(0, 4).map((decision) => (
            <Ga4DecisionCard
              key={`measurement-${decision.id}`}
              decision={decision}
            />
          ))}
        </div>
      ) : (
        <BlockerNotice message="Brak aktywnych problemów pomiaru w top kolejce GA4. Wnioski o konwersjach, zwrot z reklam i przychody nadal pozostają zablokowane bez właściwych metryk." />
      )}
    </section>
  );
}

function Ga4OperatorSummary({
  data,
  connectorStatuses
}: {
  data: Ga4DiagnosticsResponse;
  connectorStatuses: ConnectorStatus[];
}) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter(
      (decision): decision is Ga4DecisionItem =>
        decision !== undefined && decision.decision_type !== "fix_measurement"
    );
  const conversionReadiness = data.conversion_readiness_contract;
  const trackingSection = data.sections.find((section) => section.id === "ga4_tracking_readiness");
  const actionIds = summary.action_ids;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Przegląd GA4
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            {summary.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Grupy ruchu" value={data.landing_group_count} />
          <MetricTile label="Pomiar" value={summary.measurement_issue_count} />
          <MetricTile label="Brak WP" value={summary.wordpress_missing_count} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <Ga4DecisionCard
                key={decision.id}
                decision={decision}
              />
            ))
          ) : (
            <BlockerNotice message="Problemy pomiaru są w sekcji powyżej. Brak osobnych decyzji jakości ruchu do pokazania w operatorze GA4." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb analityki</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine
              label="Świeżość danych"
              values={[
                data.freshness_assessment.state_label,
                data.freshness_assessment.summary
              ]}
            />
            <TraceLine
              label="Gotowość pomiaru"
              values={
                trackingSection
                  ? [trackingSection.status_label, trackingSection.summary]
                  : []
              }
              empty="brak"
            />
            <TraceLine
              label="Konwersje i zdarzenia kluczowe"
              values={[
                conversionReadiness.status_label,
                conversionReadiness.summary
              ]}
            />
            <TraceLine
              label="Brakujące dane"
              values={conversionReadiness.missing_read_contract_labels}
              empty="brak"
            />
            <TraceLine
              label="Dowody w WILQ"
              values={[formatGa4EvidenceCount(data.evidence_ids.length)]}
            />
            <TraceLine
              label="Akcje"
              values={[formatGa4ActionCount(actionIds.length)]}
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={summary.blocked_claim_labels}
            />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Sprawdź GA4 w WILQ
            </a>
          ) : null}
        </div>
      </div>
    </section>
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
          <StatusBadge value={decision.status_label} />
          <StatusBadge value={decision.risk_label} />
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
          empty="brak"
        />
        <TraceLine label="Źródła" values={decision.source_connector_labels} empty="brak" />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[formatGa4ActionCount(decision.action_ids.length)]}
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
  const sourceConnectorLabels = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connector_labels),
    ...data.decision_queue.flatMap((decision) => decision.source_connector_labels)
  ]);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót źródeł i blokad w WILQ. Decyzje dla marketera są powyżej;
            tutaj widać, z jakich źródeł i blokad wynikają.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Obszary danych" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Dowody" value={formatGa4EvidenceCount(data.evidence_ids.length)} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? <Ga4MetricTiles facts={visibleMetricFacts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => section.label)} />
        <TraceLine label="Dowody" values={[formatGa4EvidenceCount(data.evidence_ids.length)]} />
        <TraceLine label="Źródła" values={sourceConnectorLabels} empty="brak" />
        <TraceLine label="Akcje" values={[formatGa4ActionCount(data.action_ids.length)]} />
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

function formatGa4EvidenceCount(count: number) {
  if (count === 0) return "brak dowodów źródłowych";
  if (count === 1) return "1 dowód źródłowy";
  if (count >= 2 && count <= 4) return `${count} dowody źródłowe`;
  return `${count} dowodów źródłowych`;
}

function formatGa4ActionCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 akcja";
  return `${count} akcji`;
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
