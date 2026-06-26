import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ShieldAlert } from "lucide-react";

import {
  ActionObject,
  ConnectorStatus,
  Ga4DiagnosticsResponse,
  getActions,
  getConnectors,
  getGa4Diagnostics
} from "../lib/api";
import { connectorLabelsFromStatuses } from "../lib/connectorLabels";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { ActionObjectFocus } from "./ActionObjectPanels";

type Ga4DecisionItem = Ga4DiagnosticsResponse["decision_queue"][number];
type Ga4MetricFact = Ga4DiagnosticsResponse["sections"][number]["metric_facts"][number];

type Ga4TrackingQualityPreviewItem = {
  action_id: string;
  id: string;
  preview_contract: string;
  operation_type: string;
  landing_page?: string | null;
  source_medium?: string | null;
  campaign_name?: string | null;
  tracking_dimension_gaps: string[];
  metric_snapshot: Record<string, string | number>;
  reason: string;
  required_validation: string[];
  blocked_claims: string[];
  evidence_ids: string[];
  apply_allowed: boolean;
  api_mutation_ready: boolean;
  destructive: boolean;
};



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
        <BlockerNotice message="Nie udało się odczytać /api/actions. GA4 route nie może pokazać sprawdzenia ani podglądu zmian." />
      </main>
    );
  }
  if (connectors.error || !connectors.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/connectors. GA4 nie może pokazać źródeł danych językiem marketera." />
      </main>
    );
  }

  const data = diagnostics.data;
  const connectorStatuses = connectors.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const trackingPreviewItems = ga4TrackingQualityPreviewItemsFromActions(routeActions);
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">GA4</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok GA4 z WILQ. Pokazuje jakość ruchu ze stron wejścia,
            dopasowanie WordPress i problemy pomiaru bez udawania konwersji, ROAS
            albo revenue.
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
              {data.connector.label}: {ga4ConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {ga4FreshnessLabel(data.freshness_assessment.state)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki GA4 dostępne" : "brak metryk GA4"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {ga4RefreshStatusLabel(latestRefresh.status)}
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
        trackingPreviewItems={trackingPreviewItems}
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
  trackingPreviewItems,
  connectorStatuses
}: {
  data: Ga4DiagnosticsResponse;
  trackingPreviewItems: Ga4TrackingQualityPreviewItem[];
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
            pełny przegląd, gdy chcesz zobaczyć `(not set)`, dowody, podgląd
            przeglądu i bramę bezpieczeństwa GA4.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Pomiar" value={data.operator_summary.measurement_issue_count} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
          <MetricTile label="Podglądy" value={trackingPreviewItems.length} />
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
          <Ga4DiagnosticProof data={data} connectorStatuses={connectorStatuses} />
          {trackingPreviewItems.length > 0 ? (
            <section className="rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                Podgląd przeglądu GA4
              </h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                Kolejka akcji do sprawdzenia. Pokazuje co sprawdzić w
                strona wejścia, źródło ruchu i kampania i nie zapisuje zmian w GA4.
              </p>
            </div>
            <MetricTile label="Pozycje" value={trackingPreviewItems.length} />
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            {trackingPreviewItems.slice(0, 4).map((preview) => (
              <Ga4TrackingQualityPreviewCard key={preview.id} preview={preview} />
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
          values={ga4BlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
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

  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Akcje do sprawdzenia
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            WILQ ma {actionCountLabel} dla GA4. Otwórz ją dopiero wtedy, gdy
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
            Wiersze `(not set)` i tracking gaps są problemem pomiaru lub
            atrybucji. WILQ pokazuje je osobno, żeby nie mieszać ich z oceną
            jakości landingu albo kampanii.
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
              connectorStatuses={connectorStatuses}
            />
          ))}
        </div>
      ) : (
        <BlockerNotice message="Brak aktywnych `(not set)`/tracking-gap decyzji w top kolejce GA4. Wnioski o konwersjach, ROAS i revenue nadal pozostają zablokowane bez właściwych metryk." />
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
            Operator GA4
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
                connectorStatuses={connectorStatuses}
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
                ga4FreshnessLabel(data.freshness_assessment.state),
                data.freshness_assessment.summary
              ]}
            />
            <TraceLine
              label="Gotowość pomiaru"
              values={
                trackingSection
                  ? [ga4SectionStatusLabel(trackingSection.status), trackingSection.summary]
                  : []
              }
              empty="brak"
            />
            <TraceLine
              label="Konwersje i zdarzenia kluczowe"
              values={[
                ga4ConversionReadinessStatusLabel(conversionReadiness.status),
                conversionReadiness.summary
              ]}
            />
            <TraceLine
              label="Braki kontraktu"
              values={conversionReadiness.missing_read_contracts.map(ga4ReadContractLabel)}
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
              values={ga4BlockedClaimLabels(summary.blocked_claims)}
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
  decision,
  connectorStatuses
}: {
  decision: Ga4DecisionItem;
  connectorStatuses: ConnectorStatus[];
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {ga4DecisionTypeLabel(decision.decision_type)}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <StatusBadge value={ga4DecisionStatusLabel(decision.status)} />
          <StatusBadge value={decision.risk} />
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
            Landing: {decision.landing_page}
          </span>
        ) : null}
        {decision.source_medium ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Źródło: {decision.source_medium}
          </span>
        ) : null}
        {decision.campaign_name ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Kampania: {decision.campaign_name}
          </span>
        ) : null}
        {decision.wordpress_match ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            WordPress: {wordpressMatchLabel(decision.wordpress_match)}
          </span>
        ) : null}
        {decision.wordpress_match_confidence ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            Dopasowanie: {wordpressMatchConfidenceLabel(decision.wordpress_match_confidence)}
          </span>
        ) : null}
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Dowody w WILQ"
          values={[formatGa4EvidenceCount(decision.evidence_ids.length)]}
        />
        <TraceLine label="Źródła" values={connectorLabelsFromStatuses(decision.source_connectors, connectorStatuses)} />
        <TraceLine
          label="Akcje do sprawdzenia"
          values={[formatGa4ActionCount(decision.action_ids.length)]}
        />
        <TraceLine label="Nie wolno twierdzić" values={ga4BlockedClaimLabels(decision.blocked_claims)} />
      </div>
      {decision.metric_facts.length > 0 ? (
        <Ga4MetricTiles facts={decision.metric_facts.slice(0, 5)} />
      ) : null}
    </article>
  );
}

function Ga4TrackingQualityPreviewCard({
  preview
}: {
  preview: Ga4TrackingQualityPreviewItem;
}) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">
            {preview.landing_page ? `Strona wejścia ${preview.landing_page}` : "Brak strony wejścia"}
          </h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {ga4OperationLabel(preview.operation_type)} /{" "}
            {preview.apply_allowed ? "zapis możliwy" : "zapis zablokowany"}
          </p>
        </div>
        <StatusBadge value={preview.tracking_dimension_gaps.length ? "blocked" : "ready"} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{preview.reason}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Źródło" values={[preview.source_medium ?? "brak źródła i medium ruchu"]} />
        <TraceLine label="Kampania" values={[preview.campaign_name ?? "brak kampanii"]} />
        <TraceLine
          label="Braki wymiarów"
          values={preview.tracking_dimension_gaps.map(ga4TrackingDimensionLabel)}
          empty="brak"
        />
        <TraceLine
          label="Warunki sprawdzenia"
          values={preview.required_validation.map(ga4ValidationLabel).slice(0, 4)}
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={ga4BlockedClaimLabels(preview.blocked_claims).slice(0, 5)}
        />
        <LinkedTraceLine label="Dowody" values={preview.evidence_ids.slice(0, 3)} kind="evidence" />
        <TraceLine label="Akcja" values={["1 akcja do sprawdzenia"]} />
      </div>
      {Object.keys(preview.metric_snapshot).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {Object.entries(preview.metric_snapshot)
            .slice(0, 4)
            .map(([label, value]) => (
              <MetricTile key={`${preview.id}-${label}`} label={label} value={value} />
            ))}
        </div>
      ) : null}
    </article>
  );
}

function ga4TrackingQualityPreviewItemsFromActions(
  actions: ActionObject[]
): Ga4TrackingQualityPreviewItem[] {
  return actions.flatMap((action) => {
    const rows = action.payload.payload_preview;
    if (!Array.isArray(rows)) return [];
    return rows
      .filter(isGa4TrackingQualityPreviewItem)
      .map((row) => ({ ...row, action_id: action.id }));
  });
}

function isGa4TrackingQualityPreviewItem(
  value: unknown
): value is Omit<Ga4TrackingQualityPreviewItem, "action_id"> {
  if (!isPlainObject(value)) return false;
  return (
    typeof value.id === "string" &&
    value.preview_contract === "ga4_tracking_quality_review_v1" &&
    typeof value.operation_type === "string" &&
    Array.isArray(value.tracking_dimension_gaps) &&
    value.tracking_dimension_gaps.every((item) => typeof item === "string") &&
    isMetricSnapshot(value.metric_snapshot) &&
    typeof value.reason === "string" &&
    Array.isArray(value.required_validation) &&
    Array.isArray(value.blocked_claims) &&
    Array.isArray(value.evidence_ids) &&
    typeof value.apply_allowed === "boolean" &&
    typeof value.api_mutation_ready === "boolean" &&
    typeof value.destructive === "boolean"
  );
}

function isMetricSnapshot(value: unknown): value is Record<string, string | number> {
  if (!isPlainObject(value)) return false;
  return Object.values(value).every(
    (item) => typeof item === "string" || typeof item === "number"
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function wordpressMatchLabel(value: string) {
  if (value === "found") return "potwierdzony";
  if (value === "missing") return "brak potwierdzenia";
  return value;
}

function wordpressMatchConfidenceLabel(value: string) {
  if (value === "exact_url") return "dokładny URL";
  if (value === "host_alias_sitemap") return "alias hosta z sitemap";
  if (value === "path_fallback") return "dopasowanie ścieżki";
  if (value === "missing") return "brak dopasowania";
  return value;
}

function Ga4DiagnosticProof({
  data,
  connectorStatuses
}: {
  data: Ga4DiagnosticsResponse;
  connectorStatuses: ConnectorStatus[];
}) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  const visibleEvidenceIds = data.evidence_ids.slice(0, 2);
  const sourceConnectors = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connectors),
    ...data.decision_queue.flatMap((decision) => decision.source_connectors)
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
          <MetricTile label="Sekcje API" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Łącznie dowodów" value={data.evidence_ids.length} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? <Ga4MetricTiles facts={visibleMetricFacts} /> : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={data.sections.map((section) => ga4SectionLabel(section.id))} />
        <LinkedTraceLine label="Przykładowe dowody" values={visibleEvidenceIds} kind="evidence" />
        <TraceLine label="Źródła" values={connectorLabelsFromStatuses(sourceConnectors, connectorStatuses)} />
        <TraceLine label="Akcje" values={[formatGa4ActionCount(data.action_ids.length)]} />
        <TraceLine
          label="Nie wolno twierdzić"
          values={ga4BlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
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
          label={ga4MetricFactLabel(fact.name)}
          value={formatGa4MetricValue(fact.value)}
        />
      ))}
    </div>
  );
}

function ga4MetricFactLabel(metricName: string) {
  const labels: Record<string, string> = {
    active_users: "Aktywni użytkownicy",
    engagement_rate: "Zaangażowanie",
    event_count: "Zdarzenia",
    screen_page_views: "Wyświetlenia stron",
    sessions: "Sesje"
  };
  return labels[metricName] ?? metricName;
}

function formatGa4MetricValue(value: string | number | boolean) {
  if (typeof value === "boolean") return value ? "tak" : "nie";
  return value;
}

function formatGa4EvidenceCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 ID";
  return `${count} ID`;
}

function formatGa4ActionCount(count: number) {
  if (count === 0) return "brak";
  if (count === 1) return "1 akcja";
  return `${count} akcji`;
}

function ga4DecisionTypeLabel(decisionType: Ga4DecisionItem["decision_type"]) {
  if (decisionType === "fix_measurement") return "problem pomiaru";
  if (decisionType === "review_landing_mapping") return "sprawdzenie mapowania landingu";
  return "kontrola jakości ruchu";
}

function ga4DecisionStatusLabel(status: Ga4DecisionItem["status"]) {
  if (status === "blocked") return "zablokowane";
  return "gotowe";
}

function ga4SectionLabel(sectionId: string) {
  if (sectionId === "ga4_landing_behavior") return "Jakość ruchu ze stron wejścia";
  if (sectionId === "ga4_tracking_readiness") return "Gotowość pomiaru konwersji";
  if (sectionId === "ga4_action_safety") return "Bezpieczeństwo akcji GA4";
  return sectionId;
}

function ga4SectionStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "zablokowane";
  if (status === "missing") return "brak metryk konwersji";
  return status;
}

function ga4ConversionReadinessStatusLabel(status: string) {
  if (status === "ready") return "gotowe";
  if (status === "blocked") return "blokuje wnioski o konwersjach";
  return status;
}

function ga4ReadContractLabel(value: string) {
  const labels: Record<string, string> = {
    conversion_or_key_event_mapping: "mapowanie konwersji i zdarzeń kluczowych",
    conversion_or_key_event_metric_facts: "metryki konwersji i zdarzeń kluczowych"
  };
  return labels[value] ?? value;
}

function ga4TrackingDimensionLabel(value: string) {
  const labels: Record<string, string> = {
    landing_page: "strona wejścia",
    source_medium: "źródło i medium ruchu",
    campaign_name: "kampania"
  };
  return labels[value] ?? value;
}

function ga4OperationLabel(value: string) {
  const labels: Record<string, string> = {
    tracking_quality_review: "ocena jakości pomiaru"
  };
  return labels[value] ?? value;
}

function ga4ValidationLabel(value: string) {
  const labels: Record<string, string> = {
    review_landing_page_dimension: "sprawdź stronę wejścia",
    review_source_medium_dimension: "sprawdź źródło i medium ruchu",
    review_campaign_name_dimension: "sprawdź kampanię",
    review_conversion_or_key_event_mapping: "sprawdź konwersje i zdarzenia kluczowe",
    human_confirm_before_tracking_change: "potwierdź sprawdzenie przez człowieka"
  };
  return labels[value] ?? value;
}

function ga4ConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje dostępu";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function ga4RefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function ga4FreshnessLabel(status: Ga4DiagnosticsResponse["freshness_assessment"]["state"]) {
  if (status === "fresh") return "dane świeże";
  if (status === "stale") return "dane do odświeżenia";
  if (status === "missing") return "brak odczytu";
  return "odczyt zablokowany";
}

function ga4BlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "attribution verdict": "werdykt atrybucji",
    "campaign quality": "jakość kampanii",
    "conversion drop": "spadek konwersji",
    "conversion rate": "conversion rate",
    "conversion setup applied": "konfiguracja konwersji zapisana",
    "funnel diagnosis": "diagnoza lejka",
    "funnel dropoff": "spadek w lejku",
    "GA4 write": "zapis do GA4",
    "profitability": "opłacalność",
    "revenue": "revenue",
    "ROAS": "ROAS",
    "tracking fixed": "pomiar naprawiony",
    "tracking gap": "problem pomiaru"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
