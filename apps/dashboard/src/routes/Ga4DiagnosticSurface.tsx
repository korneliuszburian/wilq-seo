import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import {
  ActionObject,
  Ga4DiagnosticsResponse,
  getActions,
  getGa4Diagnostics
} from "../lib/api";
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

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/ga4/diagnostics. GA4 route nie może udawać behavior ani conversion insightów bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. GA4 route nie może pokazać walidacji ani podglądu payloadu." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const trackingPreviewItems = ga4TrackingQualityPreviewItemsFromActions(routeActions);
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">GA4</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok GA4 z WILQ API. Pokazuje jakość ruchu z landingów,
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
              {data.connector.id}: {ga4ConnectorStatusLabel(data.connector.status)}
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

      <Ga4MeasurementIssues data={data} />
      <Ga4OperatorSummary data={data} />

      <Ga4DiagnosticProof data={data} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

      {trackingPreviewItems.length > 0 ? (
        <section className="mt-6 rounded-md border border-line bg-white p-4">
          <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
                Podgląd review GA4
              </h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                Review-only kolejka z ActionObject. Pokazuje co sprawdzić w
                landing/source/campaign i nie wykonuje zmian w GA4.
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

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa GA4
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              WILQ może przygotować review jakości ruchu i checklistę pomiaru, ale
              nie może uznać wyniku za problem kampanii bez konwersji, kosztów i
              walidacji ActionObject.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={ga4BlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </section>
    </main>
  );
}

function Ga4MeasurementIssues({ data }: { data: Ga4DiagnosticsResponse }) {
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
            <Ga4DecisionCard key={`measurement-${decision.id}`} decision={decision} />
          ))}
        </div>
      ) : (
        <BlockerNotice message="Brak aktywnych `(not set)`/tracking-gap decyzji w top kolejce GA4. Wnioski o konwersjach, ROAS i revenue nadal pozostają zablokowane bez właściwych metryk." />
      )}
    </section>
  );
}

function Ga4OperatorSummary({ data }: { data: Ga4DiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is Ga4DecisionItem => Boolean(decision));
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
              <Ga4DecisionCard key={decision.id} decision={decision} />
            ))
          ) : (
            <BlockerNotice message="Brak decyzji GA4. Najpierw uruchom odczyt GA4." />
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
              label="Konwersje / key events"
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
              label="Dowody w API"
              values={[formatGa4EvidenceCount(data.evidence_ids.length)]}
            />
            <TraceLine
              label="ActionObject"
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
              Waliduj review GA4
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function Ga4DecisionCard({ decision }: { decision: Ga4DecisionItem }) {
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
          label="Dowody w API"
          values={[formatGa4EvidenceCount(decision.evidence_ids.length)]}
        />
        <TraceLine label="Źródła" values={decision.source_connectors} />
        <TraceLine
          label="Akcje do walidacji"
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
            {preview.landing_page ? `Landing ${preview.landing_page}` : "Brak landing page"}
          </h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {preview.operation_type} / {preview.apply_allowed ? "apply możliwy" : "apply zablokowany"}
          </p>
        </div>
        <StatusBadge value={preview.tracking_dimension_gaps.length ? "blocked" : "review"} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-700">{preview.reason}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Źródło" values={[preview.source_medium ?? "brak source/medium"]} />
        <TraceLine label="Kampania" values={[preview.campaign_name ?? "brak kampanii"]} />
        <TraceLine
          label="Braki wymiarów"
          values={preview.tracking_dimension_gaps.map(ga4TrackingDimensionLabel)}
          empty="brak"
        />
        <TraceLine
          label="Walidacje"
          values={preview.required_validation.map(ga4ValidationLabel).slice(0, 4)}
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={ga4BlockedClaimLabels(preview.blocked_claims).slice(0, 5)}
        />
        <LinkedTraceLine label="Dowody" values={preview.evidence_ids.slice(0, 3)} kind="evidence" />
        <LinkedTraceLine label="ActionObject" values={[preview.action_id]} kind="actions" />
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

function Ga4DiagnosticProof({ data }: { data: Ga4DiagnosticsResponse }) {
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
            To jest skrót kontraktu WILQ API. Decyzje dla marketera są powyżej;
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
        <TraceLine label="Źródła" values={sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" />
        <TraceLine
          label="Zablokowane claimy"
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
  if (count === 1) return "1 ActionObject";
  return `${count} ActionObjecty`;
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
  if (sectionId === "ga4_landing_behavior") return "Jakość ruchu z landingów";
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
    conversion_or_key_event_mapping: "mapowanie konwersji / key events",
    conversion_or_key_event_metric_facts: "metryki konwersji / key events"
  };
  return labels[value] ?? value;
}

function ga4TrackingDimensionLabel(value: string) {
  const labels: Record<string, string> = {
    landing_page: "landing page",
    source_medium: "source / medium",
    campaign_name: "kampania"
  };
  return labels[value] ?? value;
}

function ga4ValidationLabel(value: string) {
  const labels: Record<string, string> = {
    review_landing_page_dimension: "sprawdź landing page",
    review_source_medium_dimension: "sprawdź source / medium",
    review_campaign_name_dimension: "sprawdź kampanię",
    review_conversion_or_key_event_mapping: "sprawdź konwersje / key events",
    human_confirm_before_tracking_change: "potwierdź review człowieka"
  };
  return labels[value] ?? value;
}

function ga4ConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
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
    "conversion setup applied": "konfiguracja konwersji wdrożona",
    "funnel diagnosis": "diagnoza lejka",
    "funnel dropoff": "spadek w lejku",
    "GA4 write": "zapis do GA4",
    "landing page quality": "jakość landing page",
    "message match": "message match",
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
