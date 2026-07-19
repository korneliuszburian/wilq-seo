import { useMemo, useState } from "react";

import type { ContentWorkItemQueueResponse } from "../lib/api";
import type { ContentWorkItemQueueCandidate } from "../lib/api";

export function ContentCandidateQueuePanel({
  queue,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  queue: ContentWorkItemQueueResponse;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const [search, setSearch] = useState("");
  const visibleCandidates = useMemo(
    () => queue.candidates.filter((candidate) => matchesContentQueueCandidate(candidate, search)),
    [queue.candidates, search]
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
        Pokazano {visibleCandidates.length} z {queue.candidate_count} propozycji.
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
            <p className="mt-2 leading-6 text-slate-600">{candidate.reason}</p>
            <div className="mt-2 text-xs text-slate-500">
              {candidate.evidence_ids.length} źródła · {candidate.measurement_readiness.label}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
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
    candidate.final_canonical_url
  ]
    .filter(Boolean)
    .some((value) => value!.toLocaleLowerCase("pl-PL").includes(normalizedSearch));
}

function FactTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2">
      <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">{label}</div>
      <div className="mt-1 text-sm font-semibold text-ink">{value}</div>
    </div>
  );
}
