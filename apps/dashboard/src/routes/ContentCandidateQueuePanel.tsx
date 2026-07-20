import { useMemo, useState } from "react";

import type {
  ContentInventoryCatalogResponse,
  ContentWorkItemQueueCandidate,
  ContentWorkItemQueueResponse
} from "../lib/api";

const DEFAULT_VISIBLE_CANDIDATES = 12;

export function ContentCandidateQueuePanel({
  queue,
  inventory,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  queue: ContentWorkItemQueueResponse;
  inventory?: ContentInventoryCatalogResponse | null;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [showAllCandidates, setShowAllCandidates] = useState(false);
  const filteredCandidates = useMemo(
    () => queue.candidates.filter((candidate) => matchesContentQueueCandidate(candidate, search)),
    [queue.candidates, search]
  );
  const visibleCandidates = useMemo(
    () => contentQueueVisibleCandidates(filteredCandidates, showAllCandidates),
    [filteredCandidates, showAllCandidates]
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Wybierz stronę do pracy</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{queue.operator_summary}</p>
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-2">
          <FactTile label="Propozycje" value={`${queue.candidate_count}`} />
          <FactTile label="Gotowe do pracy" value={`${queue.actionable_candidate_count}`} />
        </div>
      </div>
      <label className="mt-4 block max-w-2xl text-sm font-medium text-slate-700">
        Szukaj strony, usługi lub zapytania
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="np. BDO, doradztwo, /oferta/"
          className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink outline-none focus:border-action focus:ring-2 focus:ring-action/20"
        />
      </label>
      <p className="mt-3 text-xs text-slate-500">
        Pokazano {visibleCandidates.length} z {filteredCandidates.length} pasujących propozycji.
      </p>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        {visibleCandidates.map((candidate) => (
          <button
            key={candidate.work_item_id}
            type="button"
            className={`rounded-md border p-3 text-left text-sm ${
              candidate.work_item_id === selectedWorkItemId ? "border-action bg-action/10" : "border-line bg-surface"
            }`}
            onClick={() => onSelectWorkItem(candidate.work_item_id)}
          >
            <div className="font-semibold text-ink">{candidate.title}</div>
            <div className="mt-1 text-xs font-medium uppercase tracking-normal text-slate-500">
              {candidate.recommended_mode_label} · {candidate.status_label}
            </div>
            <div className="mt-2 rounded border border-line bg-white/70 px-2 py-1.5 text-xs text-slate-700" data-testid={`content-candidate-evidence-${candidate.work_item_id}`}>
              {candidateEvidenceSummary(candidate, inventory)}
            </div>
            <p className="mt-2 leading-6 text-slate-600">{candidate.reason}</p>
            <div className="mt-2 text-xs text-slate-500">
              {candidate.evidence_ids.length} źródła · {candidate.measurement_readiness.label}
            </div>
          </button>
        ))}
      </div>
      {filteredCandidates.length > DEFAULT_VISIBLE_CANDIDATES ? (
        <button
          type="button"
          className="mt-4 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-action"
          onClick={() => setShowAllCandidates((value) => !value)}
        >
          {showAllCandidates
            ? "Pokaż krótszą kolejkę"
            : `Pokaż wszystkie propozycje (${filteredCandidates.length})`}
        </button>
      ) : null}
    </section>
  );
}

export function contentQueueVisibleCandidates(
  candidates: ContentWorkItemQueueCandidate[],
  showAll: boolean
): ContentWorkItemQueueCandidate[] {
  return showAll ? candidates : candidates.slice(0, DEFAULT_VISIBLE_CANDIDATES);
}

export function matchesContentQueueCandidate(
  candidate: ContentWorkItemQueueCandidate,
  search: string
): boolean {
  const normalizedSearch = search.trim().toLocaleLowerCase("pl-PL");
  if (!normalizedSearch) return true;
  return [
    candidate.title,
    candidate.topic,
    candidate.reason,
    candidate.source_public_url,
    candidate.final_canonical_url,
    candidate.page_inventory?.content_summary,
    ...(candidate.page_inventory?.section_headings ?? []),
    ...(candidate.page_inventory?.acf_section_headings ?? [])
  ]
    .filter(Boolean)
    .some((value) => value!.toLocaleLowerCase("pl-PL").includes(normalizedSearch));
}

export function candidateEvidenceSummary(
  candidate: ContentWorkItemQueueCandidate,
  inventory?: ContentInventoryCatalogResponse | null
): string {
  const metrics = candidate.search_metrics;
  const metricParts: string[] = [];
  if (metrics?.impressions !== null && metrics?.impressions !== undefined) {
    metricParts.push(`${metrics.impressions.toLocaleString("pl-PL")} wyśw.`);
  }
  if (metrics?.clicks !== null && metrics?.clicks !== undefined) {
    metricParts.push(`${metrics.clicks.toLocaleString("pl-PL")} klik.`);
  }
  if (metrics?.ctr !== null && metrics?.ctr !== undefined) {
    metricParts.push(`CTR ${(metrics.ctr * 100).toLocaleString("pl-PL", { maximumFractionDigits: 2 })}%`);
  }
  if (metrics?.best_average_position !== null && metrics?.best_average_position !== undefined) {
    metricParts.push(`poz. ${metrics.best_average_position.toLocaleString("pl-PL", { maximumFractionDigits: 1 })}`);
  }
  if (metrics?.query_count) metricParts.push(`${metrics.query_count} zapytań`);
  if (metrics?.primary_query) metricParts.push(`query: „${metrics.primary_query}”`);
  if (metrics?.comparison_status === "available" && metrics.comparison_periods?.length === 2) {
    metricParts.push(`porównanie: ${metrics.comparison_periods[0]} → ${metrics.comparison_periods[1]}`);
  } else if (metrics?.comparison_status === "ambiguous") {
    metricParts.push("porównanie niejednoznaczne");
  } else if (metrics?.comparison_status === "not_available") {
    metricParts.push("brak porównywalnego okresu");
  }
  if (metricParts.length) {
    const ga4 = candidate.ga4_metrics;
    if (ga4?.status === "available" && ga4.metrics.length) {
      const ga4Summary = ga4.metrics
        .slice(0, 4)
        .map((metric) => `${metric.metric_label || metric.name}: ${metric.value}`)
        .join(", ");
      metricParts.push(`GA4: ${ga4Summary}`);
    } else {
      metricParts.push("GA4: brak exact danych");
    }
  }
  const queueInventory = candidate.page_inventory;
  const candidatePath = normalizedInventoryPath(candidate.final_canonical_url ?? candidate.source_public_url);
  const catalogItem = inventory?.items.find(
    (item) =>
      item.work_item_id === candidate.work_item_id ||
      normalizedInventoryPath(item.url) === candidatePath
  );
  const sectionCount = catalogItem?.section_count ?? queueInventory?.section_count;
  if (catalogItem && sectionCount !== null && sectionCount !== undefined) {
    metricParts.push(`${sectionCount} nagłówków inventory WordPress`);
  } else if (sectionCount !== null && sectionCount !== undefined) {
    metricParts.push(`${sectionCount} sekcji z projekcji kolejki`);
  } else if (catalogItem?.material_status === "content_and_structure" || queueInventory?.content_inventory_status === "available") {
    metricParts.push("treść odczytana");
  }
  return metricParts.length ? metricParts.join(" · ") : "Brak exact metryk lub materiału do wyboru.";
}

function normalizedInventoryPath(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const path = new URL(url).pathname.toLocaleLowerCase("pl-PL");
    return path.length > 1 ? path.replace(/\/+$/, "") : "/";
  } catch {
    return url.trim().toLocaleLowerCase("pl-PL").replace(/\/+$/, "") || "/";
  }
}

function FactTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}
