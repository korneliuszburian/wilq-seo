import { useQuery } from "@tanstack/react-query";
import { ShieldAlert } from "lucide-react";

import {
  getActions,
  getMerchantDiagnostics,
  MerchantDiagnosticsResponse
} from "../lib/api";
import { BlockerNotice, LoadingBand, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { ActionObjectFocus } from "./ActionObjectPanels";
import { priorityLabel } from "./marketingLabels";
import {
  tacticalContextPairs,
  tacticalDimensionLabels,
  tacticalIntentLabels
} from "./TacticalQueuePanel";

type MerchantDecisionItem = MerchantDiagnosticsResponse["decision_queue"][number];
type MerchantProductPerformanceRow =
  MerchantDiagnosticsResponse["product_performance_readiness"]["performance_rows"][number];

export function MerchantDiagnosticSurface() {
  const diagnostics = useQuery({
    queryKey: ["merchant-diagnostics"],
    queryFn: getMerchantDiagnostics
  });
  const actions = useQuery({
    queryKey: ["actions"],
    queryFn: getActions
  });

  if (diagnostics.isLoading || actions.isLoading) return <LoadingBand />;
  if (diagnostics.error || !diagnostics.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/merchant/diagnostics. Merchant route nie może udawać feed insightów bez WILQ API." />
      </main>
    );
  }
  if (actions.error || !actions.data) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <BlockerNotice message="Nie udało się odczytać /api/actions. Merchant route nie może pokazać walidacji ani podglądu payloadu." />
      </main>
    );
  }

  const data = diagnostics.data;
  const routeActions = actions.data.filter((action) => data.action_ids.includes(action.id));
  const latestRefresh = data.latest_refresh;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Merchant Center</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Dedykowany widok feedu i produktów oparty o Merchant Diagnostics z WILQ API.
            Pokazuje metryki produktów, kolejkę problemów i bezpieczne akcje
            bez surowych dumpów produktów i bez obietnic naprawy feedu.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Problemy" value={data.issue_count ?? 0} />
          <MetricTile label="Dowody" value={data.evidence_ids.length} />
        </div>
      </div>

      <section className="mb-6 rounded-md border border-line bg-white p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Status Merchant Center
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
              {merchantConnectorStatusLabel(data.connector.status)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {merchantFreshnessLabel(data.freshness_assessment.state)}
            </span>
            <span className="rounded-md border border-line px-2 py-1 text-slate-600">
              {data.live_data_available ? "metryki feedu dostępne" : "brak metryk feedu"}
            </span>
            {latestRefresh ? (
              <span className="rounded-md border border-line px-2 py-1 text-slate-600">
                ostatni odczyt: {merchantRefreshStatusLabel(latestRefresh.status)}
              </span>
            ) : null}
          </div>
        </div>
      </section>

      <MerchantOperatorSummary data={data} />

      <MerchantProductSampleReadiness data={data} />

      <MerchantProductPerformanceReadiness data={data} />

      <MerchantPriceImpactReadiness data={data} />

      <MerchantUnknowns data={data} />

      <MerchantDiagnosticProof data={data} />

      {routeActions.length > 0 ? (
        <div className="mt-6">
          <ActionObjectFocus actions={routeActions} />
        </div>
      ) : null}

      <section className="mt-6 rounded-md border border-line bg-white p-4">
        <div className="mb-3 flex items-start gap-3">
          <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
            <ShieldAlert aria-hidden="true" size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
              Brama bezpieczeństwa feedu
            </h2>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Merchant Center pozostaje w trybie przeglądu i przygotowania. WILQ może pokazać
              kolejkę problemów, dowody i podgląd payloadu, ale nie może zmienić feedu,
              obiecać ponownego zatwierdzenia produktu ani wykonać zmiany bez walidacji i audytu.
            </p>
          </div>
        </div>
        <TraceLine
          label="Zablokowane claimy"
          values={merchantBlockedClaimLabels(data.sections.flatMap((section) => section.blocked_claims))}
        />
      </section>
    </main>
  );
}

function merchantConnectorStatusLabel(status: string) {
  if (status === "configured") return "dostęp skonfigurowany";
  if (status === "missing_credentials") return "brakuje credentiali";
  if (status === "disabled") return "źródło wyłączone";
  return `status: ${status}`;
}

function merchantRefreshStatusLabel(status: string) {
  if (status === "completed") return "zakończony";
  if (status === "blocked") return "zablokowany";
  if (status === "failed") return "błąd";
  if (status === "running") return "w toku";
  return status;
}

function merchantFreshnessLabel(status: MerchantDiagnosticsResponse["freshness_assessment"]["state"]) {
  if (status === "fresh") return "dane świeże";
  if (status === "stale") return "dane do odświeżenia";
  if (status === "missing") return "brak odczytu";
  return "odczyt zablokowany";
}

function MerchantOperatorSummary({ data }: { data: MerchantDiagnosticsResponse }) {
  const summary = data.operator_summary;
  const decisionsById = new Map(data.decision_queue.map((decision) => [decision.id, decision]));
  const clustersById = new Map(data.issue_clusters.map((cluster) => [cluster.id, cluster]));
  const itemsById = new Map(
    data.sections.flatMap((section) => section.tactical_items).map((item) => [item.id, item])
  );
  const topDecisions = summary.top_decision_ids
    .map((decisionId) => decisionsById.get(decisionId))
    .filter((decision): decision is MerchantDecisionItem => Boolean(decision));
  const topIssueClusters = summary.top_issue_cluster_ids
    .map((clusterId) => clustersById.get(clusterId))
    .filter((cluster): cluster is MerchantDiagnosticsResponse["issue_clusters"][number] =>
      Boolean(cluster)
    );
  const topIssueItems = summary.top_tactical_item_ids
    .map((itemId) => itemsById.get(itemId))
    .filter((item): item is MerchantDiagnosticsResponse["sections"][number]["tactical_items"][number] =>
      Boolean(item)
    );
  const actionIds = summary.action_ids;

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Operator Merchant
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-normal">
            {summary.title}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {summary.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Produkty" value={data.product_count ?? 0} />
          <MetricTile label="Decyzje" value={data.decision_queue.length} />
          <MetricTile label="Zgłoszenia" value={summary.reported_issue_occurrences} />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="grid gap-3">
          {topDecisions.length > 0 ? (
            topDecisions.map((decision) => (
              <MerchantDecisionCard key={decision.id} decision={decision} />
            ))
          ) : topIssueClusters.length > 0 ? (
            topIssueClusters.map((cluster) => (
              <article key={cluster.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      {cluster.issue_type}
                      {cluster.affected_attribute ? ` / ${cluster.affected_attribute}` : ""}
                      {` / ${merchantReportingContextLabel(cluster.reporting_context)}`}
                    </h3>
                    <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                      {cluster.severity} / {cluster.resolution ?? "brak resolution"}
                    </p>
                  </div>
                  <StatusBadge value={cluster.risk} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Raport pokazuje{" "}
                  {formatPolishCount(
                    cluster.product_count,
                    "zgłoszenie",
                    "zgłoszenia",
                    "zgłoszeń"
                  )}{" "}
                  tego problemu
                  {cluster.country ? ` w kraju ${cluster.country}` : ""}
                  {cluster.reporting_context
                    ? ` / ${merchantReportingContextLabel(cluster.reporting_context)}`
                    : " / wszystkie konteksty"}.
                </p>
                {cluster.sample_unavailable_reason ? (
                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    {cluster.sample_unavailable_reason}
                  </p>
                ) : null}
                <p className="mt-2 text-sm font-medium text-ink">{cluster.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  <span className="rounded border border-line bg-white px-2 py-1">
                    zgłoszenia: {cluster.product_count}
                  </span>
                  {cluster.country ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      kraj: {cluster.country}
                    </span>
                  ) : null}
                  <span className="rounded border border-line bg-white px-2 py-1">
                    kontekst: {merchantReportingContextLabel(cluster.reporting_context)}
                  </span>
                  {cluster.resolution ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      rozwiązanie: {cluster.resolution}
                    </span>
                  ) : null}
                  {cluster.action_id ? (
                    <span className="rounded border border-line bg-white px-2 py-1">
                      Akcja: {cluster.action_id}
                    </span>
                  ) : null}
                </div>
              </article>
            ))
          ) : topIssueItems.length > 0 ? (
            topIssueItems.map((item) => (
              <article key={item.id} className="rounded-md border border-line bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">{item.title}</h3>
                    <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                      {tacticalIntentLabels[item.intent]} / {priorityLabel(item.priority)}
                    </p>
                  </div>
                  <StatusBadge value={item.risk} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
                <p className="mt-2 text-sm font-medium text-ink">{item.next_step}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
                  {tacticalContextPairs(item).map(([key, value]) => (
                    <span key={key} className="rounded border border-line bg-white px-2 py-1">
                      {tacticalDimensionLabels[key] ?? key}: {value}
                    </span>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <BlockerNotice message="Brak Merchant tactical items. Najpierw uruchom read-only Merchant vendor_read." />
          )}
        </div>

        <div className="rounded-md border border-line bg-slate-50 p-3">
          <h3 className="text-sm font-semibold text-ink">Bezpieczny tryb pracy</h3>
          <div className="mt-3 grid gap-2 text-xs text-slate-600">
            <TraceLine label="Typy problemów" values={summary.issue_types} empty="brak" />
            <TraceLine
              label="Dowody"
              values={[formatMerchantIdCount(summary.evidence_ids.length, "ID", "ID")]}
              empty="brak"
            />
            <TraceLine
              label="Akcje"
              values={[formatMerchantIdCount(actionIds.length, "akcja", "akcji")]}
              empty="brak"
            />
            <TraceLine
              label="Nie wolno twierdzić"
              values={merchantBlockedClaimLabels(summary.blocked_claims)}
            />
          </div>
          {actionIds.length > 0 ? (
            <a
              href={`/actions/${actionIds[0]}`}
              className="mt-4 inline-flex h-9 items-center rounded-md border border-line bg-white px-3 text-sm font-medium text-ink hover:bg-slate-100"
            >
              Waliduj ActionObject
            </a>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function MerchantUnknowns({ data }: { data: MerchantDiagnosticsResponse }) {
  if (data.unknowns.length === 0) return null;
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Czego nie wiemy z Merchant API
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            Te ograniczenia blokują zbyt mocne wnioski i automatyczne zmiany feedu.
            Decision queue jest źródłem decyzji, a issue clusters są drilldownem.
          </p>
        </div>
        <MetricTile label="Ograniczenia" value={data.unknowns.length} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {data.unknowns.map((unknown) => (
          <article key={unknown.id} className="rounded-md border border-line bg-slate-50 p-3">
            <h3 className="text-sm font-semibold text-ink">{unknown.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">{unknown.reason}</p>
            <p className="mt-2 text-sm leading-6 text-slate-700">{unknown.impact}</p>
            <p className="mt-2 text-sm font-medium text-ink">{unknown.next_step}</p>
            <div className="mt-2 text-xs text-slate-600">
              <TraceLine
                label="Blokuje claimy"
                values={merchantBlockedClaimLabels(unknown.blocked_claims)}
              />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function MerchantProductSampleReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.product_sample_readiness;
  const statusLabel = readiness.sample_products_available
    ? "próbki produktów dostępne"
    : "próbki produktów zablokowane";
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Gotowość próbek produktów
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">{readiness.next_step}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs">
          <MetricTile label="Status" value={statusLabel} />
          <MetricTile label="Próbki" value={readiness.sample_count} />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Obecny odczyt" values={[readiness.current_read_contract]} />
        <TraceLine label="Endpoint źródłowy" values={[readiness.source_endpoint]} />
        <TraceLine
          label="Przykładowe produkty"
          values={readiness.sample_product_ids.length ? readiness.sample_product_ids : ["brak próbek"]}
        />
        <TraceLine
          label="Przykładowe tytuły"
          values={
            readiness.sample_product_titles.length
              ? readiness.sample_product_titles
              : ["brak tytułów"]
          }
        />
        <TraceLine label="Potrzebne kontrakty" values={readiness.required_read_contracts} />
        <TraceLine
          label="Blokuje claimy"
          values={merchantBlockedClaimLabels(readiness.blocked_claims)}
        />
      </div>
    </section>
  );
}

function MerchantProductPerformanceReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.product_performance_readiness;
  const statusLabel =
    readiness.status === "ready" ? "join performance dostępny" : "join performance zablokowany";
  const visibleRows = readiness.performance_rows.slice(0, 4);
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Join produktów z Ads/GA4
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">{readiness.next_step}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Status" value={statusLabel} />
          <MetricTile label="Join" value={readiness.joined_product_count} />
          <MetricTile label="Próbki" value={readiness.merchant_sample_count} />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Obecne kontrakty" values={readiness.current_read_contracts} />
        <TraceLine label="Potrzebne kontrakty" values={readiness.required_read_contracts} />
        <TraceLine label="Klucze joinu" values={readiness.join_key_candidates} />
        <TraceLine label="Źródła" values={readiness.source_connectors} empty="brak" />
        <LinkedTraceLine
          label="Dowody"
          values={readiness.evidence_ids.slice(0, 4)}
          kind="evidence"
        />
        <TraceLine
          label="Blokuje claimy"
          values={merchantBlockedClaimLabels(readiness.blocked_claims)}
        />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
        <MetricTile label="Ads facts" value={readiness.ads_product_fact_count} />
        <MetricTile label="GA4 facts" value={readiness.ga4_product_fact_count} />
        <MetricTile label="Sample IDs" value={readiness.sample_product_ids.length} />
        <MetricTile label="Wiersze" value={readiness.performance_rows.length} />
      </div>
      {visibleRows.length > 0 ? (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {visibleRows.map((row) => (
            <MerchantProductPerformanceRowCard key={row.product_id} row={row} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function MerchantProductPerformanceRowCard({
  row
}: {
  row: MerchantProductPerformanceRow;
}) {
  const title = row.sample_title ?? row.ads_product_title ?? row.product_id;
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      {title !== row.product_id ? (
        <p className="mt-1 break-all text-xs text-slate-500">{row.product_id}</p>
      ) : null}
      <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs">
        <MetricTile label="Status Ads" value={row.ads_product_status ?? "brak"} />
        <MetricTile label="Dostępność Ads" value={row.ads_product_availability ?? "brak"} />
        <MetricTile
          label="Cena Ads"
          value={merchantMicrosPrice(row.ads_product_price_micros, row.ads_product_currency_code)}
        />
        <MetricTile label="Kliknięcia Ads" value={row.ads_clicks ?? "brak"} />
        <MetricTile label="Koszt Ads" value={row.ads_cost_micros ?? "brak"} />
        <MetricTile label="Zakupy GA4" value={row.ga4_ecommerce_purchases ?? "brak"} />
        <MetricTile label="Przychód GA4" value={row.ga4_purchase_revenue ?? "brak"} />
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine
          label="Problem Merchant"
          values={[
            row.issue_type,
            row.affected_attribute,
            row.country,
            row.reporting_context
          ].filter((value): value is string => Boolean(value))}
          empty="brak kontekstu problemu"
        />
        <TraceLine label="Źródła" values={row.source_connectors} />
        <LinkedTraceLine label="Dowody" values={row.evidence_ids.slice(0, 4)} kind="evidence" />
        <TraceLine label="Brakujące metryki" values={row.missing_metrics} empty="brak" />
        <TraceLine
          label="Nie wolno twierdzić"
          values={merchantBlockedClaimLabels(row.blocked_claims)}
        />
      </div>
    </article>
  );
}

function MerchantPriceImpactReadiness({ data }: { data: MerchantDiagnosticsResponse }) {
  const readiness = data.price_impact_readiness;
  const preview = readiness.payload_preview[0];
  const previewProducts = merchantUnknownArray(preview?.products);
  const statusLabel =
    readiness.status === "ready" ? "price impact gotowy do review" : "price impact zablokowany";
  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Wpływ ceny produktu
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            {readiness.summary}
          </p>
          <p className="mt-2 text-sm font-medium text-ink">{readiness.next_step}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-5">
          <MetricTile label="Status" value={statusLabel} />
          <MetricTile label="Ceny teraz" value={readiness.products_with_current_price} />
          <MetricTile label="Historia cen" value={readiness.products_with_previous_price} />
          <MetricTile label="Zmiany ceny" value={readiness.products_with_price_change} />
          <MetricTile
            label="Bez zmiany"
            value={readiness.products_with_unchanged_price_history}
          />
        </div>
      </div>
      <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
        <TraceLine label="Obecne kontrakty" values={readiness.current_read_contracts} />
        <TraceLine label="Potrzebne kontrakty" values={readiness.required_read_contracts} />
        <TraceLine
          label="Brakujące kontrakty"
          values={readiness.missing_read_contracts}
          empty="brak"
        />
        <TraceLine
          label="Blokuje claimy"
          values={merchantBlockedClaimLabels(readiness.blocked_claims)}
        />
      </div>
      {preview ? (
        <div className="mt-3 rounded border border-line bg-slate-50 p-2 text-xs text-slate-600">
          <p className="font-medium text-ink">Podgląd price-impact</p>
          <TraceLine
            label="Kontrakt"
            values={[merchantString(preview.preview_contract) ?? "brak"]}
          />
          <TraceLine
            label="Produkty"
            values={[
              previewProducts.length
                ? formatMerchantIdCount(previewProducts.length, "wiersz", "wiersze")
                : "bez wierszy"
            ]}
          />
          <TraceLine
            label="Apply/API"
            values={[
              `apply=${merchantBooleanLabel(preview.apply_allowed)}`,
              `api=${merchantBooleanLabel(preview.api_mutation_ready)}`
            ]}
          />
        </div>
      ) : null}
    </section>
  );
}

function MerchantDecisionCard({ decision }: { decision: MerchantDecisionItem }) {
  return (
    <article className="rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-ink">{decision.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {merchantDecisionTypeLabel(decision.decision_type)} /{" "}
            {priorityLabel(decision.priority)}
          </p>
        </div>
        <StatusBadge value={decision.risk} />
      </div>
      {decision.summary ? (
        <p className="mt-2 text-sm leading-6 text-slate-700">{decision.summary}</p>
      ) : null}
      <p className="mt-2 text-sm leading-6 text-slate-700">{decision.rationale}</p>
      <p className="mt-2 text-sm font-medium text-ink">{decision.next_step}</p>
      {Object.keys(decision.metric_tiles ?? {}).length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(decision.metric_tiles).map(([label, value]) => (
            <MetricTile key={`${decision.id}-${label}`} label={label} value={value} />
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-700">
        {decision.issue_type ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            problem: {decision.issue_type}
          </span>
        ) : null}
        {decision.affected_attribute ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            atrybut: {decision.affected_attribute}
          </span>
        ) : null}
        {decision.country ? (
          <span className="rounded border border-line bg-white px-2 py-1">
            kraj: {decision.country}
          </span>
        ) : null}
        <span className="rounded border border-line bg-white px-2 py-1">
          kontekst: {merchantReportingContextLabel(decision.reporting_context)}
        </span>
      </div>
      <div className="mt-2 grid gap-1.5 text-xs text-slate-600">
        {decision.sample_product_ids.length || decision.sample_titles.length ? (
          <div className="rounded border border-line bg-white p-2">
            <p className="font-medium text-ink">Przykładowe produkty do review</p>
            <TraceLine
              label="ID produktów"
              values={decision.sample_product_ids.slice(0, 6)}
              empty="brak próbek"
            />
            <TraceLine
              label="Tytuły"
              values={decision.sample_titles.slice(0, 4)}
              empty="brak tytułów"
            />
            <p className="mt-1 text-xs text-slate-500">
              To są przykłady z odczytu Merchant, nie pełna lista SKU ani gotowa zmiana feedu.
            </p>
          </div>
        ) : null}
        <MerchantDecisionPreview previews={decision.payload_preview} />
        <TraceLine
          label="Dowody"
          values={[formatMerchantIdCount(decision.evidence_ids.length, "ID", "ID")]}
          empty="brak"
        />
        <TraceLine
          label="Akcje"
          values={[
            formatMerchantIdCount(decision.action_ids.length, "akcja", "akcji")
          ]}
          empty="brak"
        />
        <TraceLine
          label="Nie wolno twierdzić"
          values={merchantBlockedClaimLabels(decision.blocked_claims)}
        />
      </div>
    </article>
  );
}

function MerchantDecisionPreview({
  previews
}: {
  previews: MerchantDecisionItem["payload_preview"];
}) {
  if (!previews.length) return null;
  return (
    <div className="rounded border border-line bg-white p-2">
      <p className="font-medium text-ink">Podgląd review</p>
      <div className="mt-1 grid gap-1.5">
        {previews.map((preview, index) => {
          const candidates = merchantUnknownArray(preview.candidates);
          const products = merchantUnknownArray(preview.products);
          const rowCount = candidates.length || products.length;
          return (
            <div
              key={`${merchantString(preview.preview_contract) || "preview"}-${index}`}
              className="rounded border border-line bg-slate-50 px-2 py-1.5"
            >
              <TraceLine
                label="Kontrakt"
                values={[merchantString(preview.preview_contract) || "brak"]}
              />
              <TraceLine
                label="Zakres"
                values={[
                  rowCount
                    ? formatMerchantIdCount(rowCount, "wiersz", "wiersze")
                    : "bez wierszy"
                ]}
              />
              <TraceLine
                label="Apply/API"
                values={[
                  `apply=${merchantBooleanLabel(preview.apply_allowed)}`,
                  `api=${merchantBooleanLabel(preview.api_mutation_ready)}`
                ]}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function merchantDecisionTypeLabel(decisionType: MerchantDecisionItem["decision_type"]) {
  if (decisionType === "review_issue_cluster") return "przegląd problemu feedu";
  if (decisionType === "review_feed_status") return "przegląd statusu feedu";
  if (decisionType === "review_product_state_mapping") return "mapowanie produktu Ads";
  return "blocker odczytu Merchant";
}

function merchantUnknownArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function merchantString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function merchantBooleanLabel(value: unknown) {
  if (value === true) return "odblokowane";
  if (value === false) return "zablokowane";
  return "brak statusu";
}

function merchantMicrosPrice(value: number | null | undefined, currencyCode?: string | null) {
  if (value === null || value === undefined) return "brak";
  const amount = value / 1_000_000;
  const currency = currencyCode ?? "PLN";
  return `${amount.toFixed(2)} ${currency}`;
}

function merchantReportingContextLabel(value: string | null | undefined) {
  if (!value) return "wszystkie konteksty";
  return value;
}

function formatPolishCount(count: number, one: string, few: string, many: string) {
  const absolute = Math.abs(count);
  const lastDigit = absolute % 10;
  const lastTwoDigits = absolute % 100;
  if (absolute === 1) {
    return `${count} ${one}`;
  }
  if (
    lastDigit >= 2 &&
    lastDigit <= 4 &&
    !(lastTwoDigits >= 12 && lastTwoDigits <= 14)
  ) {
    return `${count} ${few}`;
  }
  return `${count} ${many}`;
}

function MerchantDiagnosticProof({ data }: { data: MerchantDiagnosticsResponse }) {
  const metricFacts = data.sections.flatMap((section) => section.metric_facts);
  const visibleMetricFacts = metricFacts.slice(0, 4);
  const visibleEvidenceIds = data.evidence_ids.slice(0, 2);
  const blockedClaims = merchantBlockedClaimLabels(
    data.sections.flatMap((section) => section.blocked_claims)
  );
  const sectionTitles = data.sections.map((section) => merchantSectionLabel(section.id));
  const sourceConnectors = uniqueValues([
    ...data.sections.flatMap((section) => section.source_connectors),
    ...data.issue_clusters.flatMap((cluster) => cluster.source_connectors)
  ]);
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">
            Dowody i ograniczenia Merchant
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
            To jest skrót technicznego kontraktu WILQ API. Pełna kolejka pracy
            jest powyżej; tutaj widać, z jakich sekcji i dowodów wynika przegląd.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <MetricTile label="Sekcje API" value={data.sections.length} />
          <MetricTile label="Metryki" value={metricFacts.length} />
          <MetricTile label="Łącznie dowodów" value={data.evidence_ids.length} />
        </div>
      </div>
      {visibleMetricFacts.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs md:grid-cols-4">
          {visibleMetricFacts.map((fact, index) => (
            <MetricTile
              key={`${fact.source_connector}-${fact.name}-${fact.evidence_id}-${index}`}
              label={merchantMetricFactLabel(fact.name)}
              value={fact.value}
            />
          ))}
        </div>
      ) : null}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <TraceLine label="Sekcje źródłowe" values={sectionTitles} />
        <LinkedTraceLine label="Przykładowe dowody" values={visibleEvidenceIds} kind="evidence" />
        <TraceLine label="Źródła" values={sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={data.action_ids} kind="actions" />
        <TraceLine label="Zablokowane claimy" values={blockedClaims} />
      </div>
    </section>
  );
}

function merchantMetricFactLabel(metricName: string) {
  const labels: Record<string, string> = {
    active_products: "Produkty aktywne",
    disapproved_products: "Produkty odrzucone",
    item_level_issue_count: "Zgłoszenia problemów",
    total_products: "Produkty w feedzie"
  };
  return labels[metricName] ?? metricName;
}

function merchantSectionLabel(sectionId: string) {
  if (sectionId === "merchant_feed_health") return "Metryki produktów";
  if (sectionId === "merchant_issue_queue") return "Kolejka problemów feedu";
  if (sectionId === "merchant_action_safety") return "Bezpieczeństwo akcji";
  return sectionId;
}

function merchantBlockedClaimLabels(claims: string[]) {
  const labels: Record<string, string> = {
    "approval restored": "produkt zatwierdzony ponownie",
    "automatic approval fix": "automatyczna naprawa zatwierdzenia",
    "automatic feed edit": "automatyczna zmiana feedu",
    "feed fix candidate": "kandydat naprawy feedu",
    "feed health": "ocena stanu feedu",
    "feed write": "zapis do feedu",
    "primary feed overwrite": "nadpisanie głównego feedu",
    "product approval": "zatwierdzenie produktu",
    "product data mutation": "zmiana danych produktu",
    "product fix impact": "efekt naprawy produktu",
    "product-level fix": "naprawa pojedynczego produktu",
    "product revenue recovery": "odzyskany przychód produktu",
    "product ROAS": "ROAS produktu",
    "profit uplift": "wzrost zysku",
    "revenue recovered": "odzyskany przychód",
    "Shopping/PMax product scaling": "skalowanie produktu w Shopping/PMax"
  };
  return uniqueValues(claims.map((claim) => labels[claim] ?? claim));
}

function formatMerchantIdCount(count: number, singular: string, plural: string) {
  if (count === 0) return "brak";
  if (count === 1) return `1 ${singular}`;
  return `${count} ${plural}`;
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values));
}
