import { ClipboardCheck } from "lucide-react";

import { TacticalQueueResponse } from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice, MetricTile } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";

type TacticalQueueItem = TacticalQueueResponse["items"][number];
type CompactTacticalGroup = TacticalQueueResponse["compact_groups"][number];

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
      <BlockerNotice message="Nie udało się pobrać kolejki działań. Odśwież widok albo sprawdź status WILQ." />
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
  const compactGroups = compact
    ? queue.compact_groups
        .filter((group) =>
          connectorIds
            ? group.source_connectors.some((connector) => connectorIds.includes(connector))
            : true
        )
        .slice(0, limit)
    : [];
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
              ? "Skondensowana kolejka decyzji z WILQ. Duplikaty zapytań i URL-i są zgrupowane; pełne szczegóły są w dedykowanych widokach."
              : "Gotowe taktyki z danych WILQ. Każda karta pokazuje źródła, dowody, akcje i twierdzenia, których WILQ nie wolno dopowiadać."}
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
        <BlockerNotice message="Brak taktyk dla tej trasy. Potrzebne są metryki w WILQ." />
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

function CompactTacticalCard({ group }: { group: CompactTacticalGroup }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{group.title}</h3>
          <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">{group.meta}</p>
        </div>
        <StatusBadge value={group.risk} label={group.risk_label} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{group.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{group.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine label="Dowody" values={[group.evidence_summary_label]} />
        <TraceLine label="Źródła" values={group.source_connector_labels} />
        <TraceLine
          label="Akcje"
          values={group.action_summary_label ? [group.action_summary_label] : []}
          empty="brak"
        />
        <TraceLine label="Granice wniosków" values={group.blocked_claim_labels} />
      </div>
    </article>
  );
}

export function shortPath(value: string) {
  try {
    const parsed = new URL(value);
    return parsed.pathname === "/" ? parsed.hostname : parsed.pathname;
  } catch {
    return value;
  }
}

function TacticalQueueCard({ item }: { item: TacticalQueueItem }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{item.title}</h3>
          <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-600">
            <span className="rounded border border-line bg-white px-2 py-1">
              Obszar: {item.domain_label}
            </span>
            <span className="rounded border border-line bg-white px-2 py-1">
              Zadanie: {item.intent_label}
            </span>
            <span className="rounded border border-line bg-white px-2 py-1">
              Priorytet: {item.priority_label}
            </span>
          </div>
        </div>
        <StatusBadge value={item.risk} label={item.risk_label} />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{item.diagnosis}</p>
      <p className="mt-3 text-sm font-medium text-ink">{item.next_step}</p>
      <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <TraceLine
          label="Dowody"
          values={item.evidence_summary_label ? [item.evidence_summary_label] : []}
          empty="brak dowodów do pokazania"
        />
        <TraceLine label="Źródła" values={item.source_connector_labels} />
        <TraceLine
          label="Akcje"
          values={item.action_summary_label ? [item.action_summary_label] : []}
          empty="brak akcji do sprawdzenia"
        />
        <TraceLine label="Granice wniosków" values={item.blocked_claim_labels} />
      </div>
      {item.evidence_ids.length > 0 || item.action_ids.length > 0 ? (
        <details className="mt-3 rounded border border-line bg-slate-50 p-2 text-xs text-slate-600">
          <summary className="cursor-pointer font-medium text-ink">Szczegóły techniczne</summary>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            <LinkedTraceLine label="Dowody źródłowe" values={item.evidence_ids} kind="evidence" />
            <LinkedTraceLine
              label="Akcje do sprawdzenia"
              values={item.action_ids}
              kind="actions"
              empty="brak"
            />
          </div>
        </details>
      ) : null}
      {tacticalContextPairs(item).length > 0 ? (
        <div className="mt-3 rounded border border-line bg-slate-50 p-2 text-xs text-slate-700">
          <div className="font-semibold text-ink">Kontekst</div>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {tacticalContextPairs(item).map(({ key, label, valueLabel }) => (
              <span key={key} className="rounded border border-line bg-white px-2 py-1">
                {label}: {valueLabel}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      {item.metric_facts.length > 0 ? <MetricFactChips facts={item.metric_facts.slice(0, 4)} /> : null}
    </article>
  );
}

export function tacticalContextPairs(
  item: TacticalQueueItem
): Array<{ key: string; label: string; valueLabel: string }> {
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
    .map((key) => ({
      key,
      label: item.dimension_labels[key] || "kontekst",
      valueLabel: item.dimension_value_labels[key] || "wartość do sprawdzenia"
    }));
}

function uniqueValues(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}
