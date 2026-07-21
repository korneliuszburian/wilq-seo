import { formatContentMetricValue } from "../lib/contentLabels";
import type { ContentWorkflowSnapshot } from "./contentWorkflowRuntime";

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

const SOURCE_QUALITY_LABELS: Record<string, string> = {
  google_search_console: "GSC",
  google_analytics_4: "GA4",
  google_ads: "Ads",
  ahrefs: "Ahrefs",
  localo: "Localo",
  wordpress_ekologus: "WordPress",
  wordpress_sklep: "WordPress sklep"
};

export function summarizeContentSourceQuality(
  assessment: ContentWorkflowSnapshot["freshnessAssessment"]
): string[] {
  const qualityStates = assessment.connector_quality_states ?? {};
  const warnings = Object.entries(qualityStates)
    .filter(([, state]) => state !== "verified" && state !== "unknown")
    .map(([connector, state]) => {
      const label = SOURCE_QUALITY_LABELS[connector] ?? connector;
      return `${label}: ${state === "partial" ? "odczyt częściowy" : "jakość do sprawdzenia"}`;
    });
  const settling = Object.entries(assessment.connector_settlement_states ?? {})
    .filter(([connector, state]) => state === "settling" && !warnings.some((warning) => warning.startsWith(`${SOURCE_QUALITY_LABELS[connector] ?? connector}:`)))
    .map(([connector]) => `${SOURCE_QUALITY_LABELS[connector] ?? connector}: dane się rozliczają`);
  return [...warnings, ...settling];
}

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
  data,
  onShowSources
}: {
  data: ContentWorkflowSnapshot;
  onShowSources: () => void;
}) {
  const item = data.preflight.item;
  const candidate = data.candidate;
  const metrics = candidate.search_metrics;
  const pageMetricFacts = item.metric_facts ?? [];
  const ga4MetricSummaries = summarizeGa4MetricFacts(pageMetricFacts);
  const gscSummary =
    metrics?.impressions === undefined || metrics.impressions === null
      ? "Dostępny odczyt GSC nie zawiera danych dla tej strony."
      : `Dostępny odczyt GSC: ${metrics.impressions} wyświetleń i ${metrics.clicks ?? 0} kliknięć.`;
  const ga4Summary = ga4MetricSummaries.length
    ? `Dostępne dane GA4: ${ga4MetricSummaries[0]}.`
    : "Brak exact danych GA4 ogranicza ocenę efektu.";

  return (
    <section
      aria-label="Dlaczego warto poprawić tę stronę?"
      className="wilq-enter wilq-enter-delay-2 mb-3 rounded-md border border-line bg-white px-3 py-3 shadow-sm sm:mb-4 sm:px-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Dlaczego warto poprawić tę stronę?</p>
          <p className="mt-1 max-w-4xl text-sm leading-6 text-slate-700">
            {gscSummary} {ga4Summary}
            {metrics?.primary_query ? ` Zapytanie GSC: „${metrics.primary_query}”.` : ""}
          </p>
        </div>
        <button
          type="button"
          aria-label="Otwórz źródła i ograniczenia strony"
          onClick={onShowSources}
          className="shrink-0 text-sm font-semibold text-action hover:underline"
        >
          Źródła i ograniczenia
        </button>
      </div>
    </section>
  );
}

/**
 * Prefer the full snapshot's fresh WordPress binding over the compact queue
 * projection. The queue can legitimately be stale after the page is opened;
 * showing its section count next to the fresh preflight count makes one page
 * appear to have two different structures.
 */
export function resolvedPageSectionCount(
  preflightCount: number | null | undefined,
  queueCount: number | null | undefined
): number | null {
  if (typeof preflightCount === "number" && Number.isInteger(preflightCount) && preflightCount >= 0) {
    return preflightCount;
  }
  return typeof queueCount === "number" && Number.isInteger(queueCount) && queueCount >= 0 ? queueCount : null;
}
