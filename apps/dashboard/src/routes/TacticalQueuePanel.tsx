import { ClipboardCheck } from "lucide-react";

import { MetricFact, TacticalQueueResponse } from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { marketerBlockedClaimLabels, priorityLabel } from "./marketingLabels";

type TacticalQueueItem = TacticalQueueResponse["items"][number];

export const tacticalIntentLabels: Record<TacticalQueueItem["intent"], string> = {
  content_refresh: "odświeżenie treści",
  content_create: "nowa treść",
  content_merge: "scalenie treści",
  content_block: "blokada treści",
  landing_page_quality: "jakość landing page",
  tracking_gap: "problem pomiaru",
  merchant_feed_triage: "triage feedu",
  traffic_quality_review: "jakość ruchu"
};

const tacticalDomainLabels: Record<string, string> = {
  gsc_seo: "SEO / GSC",
  ga4: "GA4",
  merchant: "Merchant",
  content: "Content"
};

export const tacticalDimensionLabels: Record<string, string> = {
  query: "Query",
  page: "Strona",
  landing_page: "Landing",
  source_medium: "Źródło",
  campaign_name: "Kampania",
  issue_type: "Issue",
  affected_attribute: "Atrybut",
  country: "Kraj",
  reporting_context: "Kontekst",
  wordpress_match: "WordPress",
  wordpress_match_confidence: "Dopasowanie WP",
  gsc_page_query_count: "Liczba query"
};

export function TacticalQueuePanel({
  queue,
  connectorIds,
  limit = 8,
  title = "Konkretne zadania z danych",
  hideTrackingGaps = false,
  compact = false,
  isLoading,
  isError
}: {
  queue?: TacticalQueueResponse;
  connectorIds?: string[];
  limit?: number;
  title?: string;
  hideTrackingGaps?: boolean;
  compact?: boolean;
  isLoading: boolean;
  isError: boolean;
}) {
  if (isError) {
    return (
      <BlockerNotice message="Nie udało się odczytać /api/marketing/tactical-queue. Dashboard nie może udawać kolejki działań." />
    );
  }
  if (isLoading || !queue) {
    return (
      <div className="rounded-md border border-line bg-white p-4 text-sm text-slate-600">
        Ładowanie kolejki taktycznej...
      </div>
    );
  }

  const filteredItems = queue.items
    .filter((item) =>
      connectorIds
        ? item.source_connectors.some((connector) => connectorIds.includes(connector))
        : true
    )
    .filter((item) => !(hideTrackingGaps && item.intent === "tracking_gap"));
  const compactGroups = compact ? compactTacticalGroups(filteredItems).slice(0, limit) : [];
  const items = compact ? [] : filteredItems.slice(0, limit);

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="mt-0.5 rounded-md border border-line bg-white p-2 text-action">
          <ClipboardCheck aria-hidden="true" size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {compact
              ? "Skondensowana kolejka decyzji z WILQ API. Duplikaty zapytań i URL-i są zgrupowane; pełny drilldown jest w dedykowanych widokach."
              : "Gotowe taktyki z wymiarowych metric facts. Każda karta pokazuje źródła, dowody, ActionObjecty i claimy, których WILQ nie wolno dopowiadać."}
          </p>
          <p className="mt-1 text-xs text-slate-500">{queue.strict_instruction}</p>
        </div>
        <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
          <MetricTile
            label={compact ? "Decyzje" : "Taktyki"}
            value={compact ? compactGroups.length : filteredItems.length}
          />
          <MetricTile label="Dowody" value={uniqueValues(filteredItems.flatMap((item) => item.evidence_ids)).length} />
          <MetricTile label="Akcje" value={uniqueValues(filteredItems.flatMap((item) => item.action_ids)).length} />
        </div>
      </div>
      {compact && compactGroups.length > 0 ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {compactGroups.map((group) => (
            <CompactTacticalCard key={group.id} group={group} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <BlockerNotice message="Brak taktyk dla tej trasy. Potrzebne są wymiarowe metric facts z WILQ API." />
      ) : (
        <div className="grid gap-3 xl:grid-cols-2">
          {items.map((item) => (
            <TacticalQueueCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}

type CompactTacticalGroup = {
  id: string;
  title: string;
  meta: string;
  diagnosis: string;
  nextStep: string;
  sourceConnectors: string[];
  evidenceIds: string[];
  actionIds: string[];
  blockedClaims: string[];
  risk: TacticalQueueItem["risk"];
};

function CompactTacticalCard({ group }: { group: CompactTacticalGroup }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{group.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">{group.meta}</p>
        </div>
        <StatusBadge value={group.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{group.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{group.nextStep}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={group.evidenceIds.slice(0, 4)} kind="evidence" />
        <TraceLine label="Źródła" values={group.sourceConnectors} />
        <LinkedTraceLine label="Akcje" values={group.actionIds} kind="actions" empty="brak" />
        <TraceLine label="Blokady claimów" values={marketerBlockedClaimLabels(group.blockedClaims)} />
      </div>
    </article>
  );
}

function compactTacticalGroups(items: TacticalQueueItem[]): CompactTacticalGroup[] {
  const groups = new Map<string, TacticalQueueItem[]>();
  for (const item of items) {
    const key = compactTacticalGroupKey(item);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return Array.from(groups.values())
    .map((groupItems) => compactTacticalGroup(groupItems))
    .sort((left, right) => prioritySortValue(left.meta) - prioritySortValue(right.meta));
}

function compactTacticalGroupKey(item: TacticalQueueItem) {
  if (item.domain === "gsc_seo" && item.dimensions.page) {
    return `${item.domain}:${item.intent}:${item.dimensions.page}`;
  }
  if (item.domain === "ga4") {
    return `${item.domain}:${item.intent}:${item.dimensions.landing_page ?? ""}:${item.dimensions.source_medium ?? ""}`;
  }
  if (item.domain === "merchant") {
    return `${item.domain}:${item.intent}:${item.dimensions.issue_type ?? ""}:${item.dimensions.affected_attribute ?? ""}:${item.dimensions.country ?? ""}`;
  }
  return item.id;
}

function compactTacticalGroup(items: TacticalQueueItem[]): CompactTacticalGroup {
  const first = items[0];
  const facts = items.flatMap((item) => item.metric_facts);
  const queries = uniqueValues(items.map((item) => item.dimensions.query).filter(Boolean));
  const clicks = sumMetricFacts(facts, "clicks");
  const impressions = sumMetricFacts(facts, "impressions");
  return {
    id: compactTacticalGroupKey(first),
    title: compactTacticalTitle(first, items.length),
    meta: `${tacticalDomainLabels[first.domain] ?? first.domain} / ${tacticalIntentLabels[first.intent]} / ${priorityLabel(first.priority)}`,
    diagnosis: compactTacticalDiagnosis(first, queries, clicks, impressions, items.length),
    nextStep: first.next_step,
    sourceConnectors: uniqueValues(items.flatMap((item) => item.source_connectors)),
    evidenceIds: uniqueValues(items.flatMap((item) => item.evidence_ids)),
    actionIds: uniqueValues(items.flatMap((item) => item.action_ids)),
    blockedClaims: uniqueValues(items.flatMap((item) => item.blocked_claims)),
    risk: first.risk
  };
}

function compactTacticalTitle(item: TacticalQueueItem, groupSize: number) {
  if (item.domain === "gsc_seo" && item.dimensions.page) {
    const action = item.intent === "content_refresh" ? "odśwież" : "zweryfikuj treść";
    return `SEO: ${action} ${shortPath(item.dimensions.page)} (${groupSize} ${polishQueryLabel(groupSize)})`;
  }
  if (item.domain === "ga4") {
    return `GA4: sprawdź ${item.dimensions.landing_page ?? "landing"} / ${item.dimensions.source_medium ?? "źródło"}`;
  }
  if (item.domain === "merchant") {
    return `Merchant: sprawdź ${merchantDimensionLabel(item.dimensions.issue_type ?? "problem feedu")} / ${merchantDimensionLabel(item.dimensions.affected_attribute ?? "atrybut")}`;
  }
  return item.title;
}

function merchantDimensionLabel(value: string) {
  const labels: Record<string, string> = {
    availability_updated: "zmiana dostępności",
    missing_potentially_required_attribute: "brak potencjalnie wymaganego atrybutu",
    "n:availability": "dostępność",
    "n:unit_pricing_measure": "miara ceny jednostkowej",
    "problem feedu": "problem feedu",
    atrybut: "atrybut"
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function compactTacticalDiagnosis(
  item: TacticalQueueItem,
  queries: string[],
  clicks: number | null,
  impressions: number | null,
  groupSize: number
) {
  if (item.domain === "gsc_seo") {
    const queryText = queries.length > 0 ? ` Query: ${queries.slice(0, 4).join(", ")}.` : "";
    const metrics = [
      clicks === null ? null : `clicks=${formatCompactNumber(clicks)}`,
      impressions === null ? null : `impressions=${formatCompactNumber(impressions)}`
    ]
      .filter(Boolean)
      .join(", ");
    return `${groupSize} powiązanych zapytań prowadzi do tej samej strony.${queryText}${metrics ? ` Suma widocznych metryk: ${metrics}.` : ""}`;
  }
  return item.diagnosis;
}

function sumMetricFacts(facts: MetricFact[], name: string) {
  const values = facts
    .filter((fact) => fact.name === name && typeof fact.value === "number")
    .map((fact) => Number(fact.value));
  if (values.length === 0) return null;
  return values.reduce((sum, value) => sum + value, 0);
}

function formatCompactNumber(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function shortPath(value: string) {
  try {
    const parsed = new URL(value);
    return parsed.pathname === "/" ? parsed.hostname : parsed.pathname;
  } catch {
    return value;
  }
}

function polishQueryLabel(count: number) {
  if (count === 1) return "zapytanie";
  if (count >= 2 && count <= 4) return "zapytania";
  return "zapytań";
}

function prioritySortValue(meta: string) {
  if (meta.includes("najpierw")) return 0;
  if (meta.includes("wysoki priorytet")) return 1;
  if (meta.includes("do sprawdzenia")) return 2;
  return 3;
}

function TacticalQueueCard({ item }: { item: TacticalQueueItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
            {tacticalDomainLabels[item.domain] ?? item.domain} /{" "}
            {tacticalIntentLabels[item.intent]} / {priorityLabel(item.priority)}
          </p>
        </div>
        <StatusBadge value={item.risk} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <LinkedTraceLine label="Dowody" values={item.evidence_ids} kind="evidence" />
        <TraceLine label="Źródła" values={item.source_connectors} />
        <LinkedTraceLine label="Akcje" values={item.action_ids} kind="actions" empty="brak" />
        <TraceLine label="Blokady claimów" values={marketerBlockedClaimLabels(item.blocked_claims)} />
      </div>
      {tacticalContextPairs(item).length > 0 ? (
        <div className="mt-3 rounded border border-line bg-slate-50 p-2 text-xs text-slate-700">
          <div className="font-semibold text-ink">Kontekst</div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {tacticalContextPairs(item).map(([key, value]) => (
              <span key={key} className="rounded border border-line bg-white px-2 py-1">
                {tacticalDimensionLabels[key] ?? key}: {value}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

export function tacticalContextPairs(item: TacticalQueueItem): Array<[string, string]> {
  const priorityKeys = [
    "query",
    "page",
    "landing_page",
    "source_medium",
    "campaign_name",
    "issue_type",
    "affected_attribute",
    "country",
    "reporting_context",
    "wordpress_match",
    "wordpress_match_confidence",
    "gsc_page_query_count"
  ];
  return priorityKeys
    .filter((key) => item.dimensions[key])
    .slice(0, 6)
    .map((key) => [key, item.dimensions[key]]);
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}
