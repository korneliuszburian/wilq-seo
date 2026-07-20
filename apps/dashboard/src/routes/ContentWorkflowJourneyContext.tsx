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
  const pageMetricFacts = item.metric_facts ?? [];
  const ga4MetricSummaries = summarizeGa4MetricFacts(pageMetricFacts);
  const sourceQualityCaveats = summarizeContentSourceQuality(data.freshnessAssessment);
  const sectionCount = resolvedPageSectionCount(
    data.preflight.item.wordpress_section_count,
    data.candidate.page_inventory?.section_count
  );
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
    sectionCount !== null
      ? `${sectionCount} rozpoznanych sekcji na stronie`
      : "Sekcje strony wymagają odczytu";

  return (
    <section
      aria-label="Kontekst zadania treściowego"
      className="wilq-enter wilq-enter-delay-2 mb-3 rounded-md border border-line bg-white p-3 shadow-sm sm:mb-4 sm:p-4"
    >
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Treści i SEO · decyzja dla strony</p>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h1 className="min-w-0 text-xl font-semibold text-ink">{pageTitle}</h1>
        <p className="text-sm font-semibold text-action">{candidate.recommended_mode_label}</p>
      </div>
      <dl className="mt-3 grid gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
        <JourneyFact label="Strona" value={publicUrl ? normalizedPath(publicUrl) : "adres wymaga sprawdzenia"} />
        <JourneyFact label="Decyzja" value={candidate.recommended_mode_label} />
      </dl>
      <div className="mt-4 grid gap-3 sm:grid-cols-3" aria-label="Najważniejsze dane dla strony">
        <JourneySignalCard
          label="Widoczność w GSC"
          value={metrics?.impressions === undefined || metrics.impressions === null ? "Brak danych" : `${metrics.impressions} wyświetleń`}
          detail={metrics?.primary_query ? `Główne zapytanie: „${metrics.primary_query}”` : "Brak exact zapytania"}
          tone="fact"
        />
        <JourneySignalCard
          label="CTR"
          value={metrics?.ctr === undefined || metrics.ctr === null ? "Brak danych" : `${(metrics.ctr * 100).toFixed(2)}%`}
          detail={metrics?.clicks === undefined || metrics.clicks === null ? comparisonSummary : `${metrics.clicks} kliknięć · ${comparisonSummary}`}
          tone="signal"
        />
        <JourneySignalCard
          label="Pomiar i struktura"
          value={sectionCount === null ? "Do odczytu" : `${sectionCount} sekcji`}
          detail={ga4MetricSummaries.length ? `GA4: ${ga4MetricSummaries[0]}` : "GA4: brak exact danych"}
          tone={sectionCount === null ? "blocker" : "fact"}
        />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3" aria-label="Fakty, sygnały i blokady">
        <EvidenceGroup title="Fakty" detail={`${candidate.source_connector_labels.join(" · ") || "Brak źródeł"} · ${data.freshnessAssessment.state_label}`} tone="fact" />
        <EvidenceGroup title="Sygnały" detail={metricSummary} tone="signal" />
        <EvidenceGroup title="Blokady" detail={ga4MetricSummaries.length ? "Brak blokady pomiaru GA4" : "Brak dokładnych danych GA4 dla strony"} tone="blocker" />
      </div>
      {sourceQualityCaveats.length ? (
        <p
          className="mt-3 rounded-md border border-wait/20 bg-wait/5 px-3 py-2 text-xs leading-5 text-slate-700"
          data-testid="content-source-quality-caveat"
        >
          Źródła do interpretacji: {sourceQualityCaveats.join(" · ")}. To jakość odczytu, nie wynik kampanii.
        </p>
      ) : null}
      <p className="sr-only" data-testid="content-ga4-metrics">
        {ga4MetricSummaries.length
          ? `GA4 dla tej strony: ${ga4MetricSummaries.join(" | ")}`
          : "GA4 dla tej strony: brak dokładnych faktów w aktualnym odczycie."}
      </p>
      <p className="sr-only" data-testid="content-metric-comparison">{comparisonSummary}</p>
      <p className="sr-only">{inventorySummary}</p>
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

function JourneySignalCard({
  label,
  value,
  detail,
  tone
}: {
  label: string;
  value: string;
  detail: string;
  tone: "fact" | "signal" | "blocker";
}) {
  const toneClass = tone === "fact" ? "border-emerald-200 bg-emerald-50/50" : tone === "signal" ? "border-amber-200 bg-amber-50/50" : "border-rose-200 bg-rose-50/50";
  return (
    <article className={`wilq-hover-lift rounded-md border p-3 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-ink">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-600">{detail}</p>
    </article>
  );
}

function EvidenceGroup({ title, detail, tone }: { title: string; detail: string; tone: "fact" | "signal" | "blocker" }) {
  const dotClass = tone === "fact" ? "bg-emerald-500" : tone === "signal" ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="wilq-hover-lift flex gap-2 rounded-md border border-line bg-surface p-3">
      <span aria-hidden="true" className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${dotClass}`} />
      <div>
        <p className="font-semibold text-ink">{title}</p>
        <p className="mt-1 text-xs leading-5 text-slate-600">{detail}</p>
      </div>
    </div>
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
