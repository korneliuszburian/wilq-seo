import { environmentLabel } from "./contentPageWorkbenchModel";
import { formatContentMetricValue } from "../lib/contentLabels";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import { normalizedPath } from "./contentWorkflowTarget";

const GA4_METRIC_PRIORITY = [
  "active_users",
  "sessions",
  "engagement_rate",
  "event_count",
  "key_events",
  "ecommerce_purchases"
] as const;

type BrowserMetricFact = NonNullable<
  ContentWorkflowSnapshot["preflight"]["item"]["metric_facts"]
>[number];

export function summarizeGa4MetricFacts(facts: BrowserMetricFact[]): string[] {
  const byName = new Map<string, BrowserMetricFact[]>();
  for (const fact of facts) {
    if (fact.source_connector !== "google_analytics_4") continue;
    const group = byName.get(fact.name) ?? [];
    group.push(fact);
    byName.set(fact.name, group);
  }
  const unknownNames = [...byName.keys()]
    // The priority list is the known operator vocabulary; every other name is
    // retained as an unknown metric and shown after the known metrics.
    .filter((name) => !GA4_METRIC_PRIORITY.includes(name as (typeof GA4_METRIC_PRIORITY)[number]))
    .sort((left, right) => left.localeCompare(right, "pl"));
  const orderedNames = [...GA4_METRIC_PRIORITY, ...unknownNames];
  return orderedNames
    .map((metricName) => {
      const group = byName.get(metricName);
      if (!group?.length) return null;
      const channels = group
        .map((fact) => ({
          channel: fact.dimensions.source_medium ?? "źródło nieopisane",
          value: formatContentMetricValue(fact.name, fact.value)
        }))
        .sort((left, right) => left.channel.localeCompare(right.channel, "pl"));
      const uniqueChannels = [...new Set(channels.map(({ channel, value }) => `${channel}: ${value}`))];
      return `${group[0].metric_label || metricName} (${uniqueChannels.join(", ")})`;
    })
    .filter((summary): summary is string => summary !== null)
    ;
}

export function ContentWorkflowJourneyContext({
  data
}: {
  data: ContentWorkflowSnapshot;
}) {
  const item = data.preflight.item;
  const candidate = data.candidate;
  const publicUrl =
    item.source_public_url ?? item.final_canonical_url ?? item.intended_final_url ?? "";
  const pageTitle =
    publicUrl && normalizedPath(publicUrl) === "/"
      ? `Strona główna ${environmentLabel(publicUrl)}`
      : item.wordpress_title_or_h1 ?? item.topic;
  const metrics = candidate.search_metrics;
  const pageInventory = candidate.page_inventory;
  const pageMetricFacts = item.metric_facts ?? [];
  const ga4MetricSummaries = summarizeGa4MetricFacts(pageMetricFacts);
  const metricSummary =
    metrics?.impressions === undefined || metrics.impressions === null
      ? "Brakuje danych z wyszukiwarki dla tej strony."
      : [
          `${metrics.impressions} wyświetleń`,
          metrics.clicks === undefined || metrics.clicks === null
            ? null
            : `${metrics.clicks} kliknięć`,
          metrics.ctr === undefined || metrics.ctr === null
            ? null
            : `CTR ${(metrics.ctr * 100).toFixed(2)}%`,
          metrics.primary_query ? `zapytanie: „${metrics.primary_query}”` : null
        ]
          .filter(Boolean)
          .join(" · ");
  const comparisonSummary =
    metrics?.comparison_status === "available" &&
    metrics.comparison_periods?.length === 2 &&
    metrics.comparison_periods.every((period) => typeof period === "string" && period.length > 0)
      ? `porównanie: ${metrics.comparison_periods[0]} → ${metrics.comparison_periods[1]}`
      : metrics?.comparison_reason ?? "Brak dwóch porównywalnych okresów — nie oceniamy trendu.";
  const inventorySummary =
    pageInventory?.section_inventory_status === "available" && pageInventory.section_count !== null
      ? `${pageInventory.section_count} rozpoznanych sekcji na stronie`
      : "Sekcje strony wymagają odczytu";

  return (
    <section
      aria-label="Kontekst zadania treściowego"
      className="mb-3 rounded-md border border-line bg-white p-3 shadow-sm sm:mb-4 sm:p-4"
    >
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Decyzja dla strony</p>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h1 className="min-w-0 text-xl font-semibold text-ink">{pageTitle}</h1>
        <p className="text-sm font-semibold text-action">{candidate.recommended_mode_label}</p>
      </div>
      <dl className="mt-3 grid gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
        <JourneyFact label="Strona" value={publicUrl ? normalizedPath(publicUrl) : "adres wymaga sprawdzenia"} />
        <JourneyFact label="Usługa" value={data.serviceProfileContext.service_label ?? "nieprzypisana"} />
        <JourneyFact label="Decyzja" value={candidate.recommended_mode_label} />
      </dl>
      <p className="mt-2 text-sm leading-6 text-slate-700">{metricSummary}</p>
      <p className="mt-1 text-xs leading-5 text-slate-600" data-testid="content-ga4-metrics">
        {ga4MetricSummaries.length
          ? `GA4 dla tej strony: ${ga4MetricSummaries.join(" | ")}`
          : "GA4 dla tej strony: brak dokładnych faktów w aktualnym odczycie."}
      </p>
      <p className="mt-1 text-xs leading-5 text-slate-500" data-testid="content-metric-comparison">
        {comparisonSummary}
      </p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{inventorySummary}</p>
      <details className="mt-3 text-xs text-slate-600">
        <summary className="cursor-pointer font-semibold text-action">Dlaczego ta decyzja?</summary>
        <p className="mt-2 leading-5">{candidate.reason}</p>
        <p className="mt-2 leading-5" data-testid="content-metric-sources">
          Źródła metryk: {candidate.source_connector_labels.length
            ? candidate.source_connector_labels.join(" · ")
            : "brak potwierdzonych źródeł"}. Stan danych: {data.freshnessAssessment.state_label}.
        </p>
        <p className="mt-2 leading-5">
          Usługa: {data.serviceProfileContext.service_label ?? "nieprzypisana"}. {publicUrl}
        </p>
      </details>
    </section>
  );
}

function JourneyFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-semibold text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-slate-700">{value}</dd>
    </div>
  );
}
