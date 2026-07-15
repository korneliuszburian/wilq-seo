import { useState } from "react";

import type {
  ContentPlanningReviewConflict,
  ContentPlanningWorkspace
} from "../lib/api";
import type { WorkflowStepId } from "./contentWorkflowRuntime";

type PlanningStage = Extract<WorkflowStepId, "scope" | "section_map">;

export type ContentPlanningReviewPanelActions = {
  conflict: ContentPlanningReviewConflict | null;
  error: Error | null;
  pending: boolean;
  refresh: () => void;
  save: (
    stage: PlanningStage,
    decision: "approved" | "needs_changes",
    notes: string,
    checkedItems: string[]
  ) => void;
};

export function ContentPlanningReviewPanel({
  actions,
  planning,
  stage
}: {
  actions: ContentPlanningReviewPanelActions;
  planning: ContentPlanningWorkspace;
  stage: PlanningStage;
}) {
  const [decision, setDecision] = useState<"approved" | "needs_changes">("approved");
  const [notes, setNotes] = useState("");
  const [checked, setChecked] = useState(false);
  const proposal = planning.proposal;
  const latestDecision = stage === "scope" ? planning.scope_decision : planning.section_map_decision;
  const canSubmit =
    !actions.pending &&
    (decision === "approved" ? checked : notes.trim().length > 0);

  return (
    <section
      aria-labelledby="planning-review-title"
      className="rounded-md border border-line bg-white p-4 shadow-sm"
      data-testid={`planning-review-${stage}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            {stage === "scope" ? "Krok 1 z 5" : "Krok 2 z 5"}
          </p>
          <h2 id="planning-review-title" className="mt-1 text-lg font-semibold text-ink">
            {stage === "scope" ? "Zatwierdź zakres treści" : "Zatwierdź plan sekcji"}
          </h2>
        </div>
        {latestDecision ? (
          <span className="rounded-md border border-line bg-surface px-3 py-2 text-xs font-semibold text-slate-600">
            Ostatnia decyzja: {latestDecision.decision === "approved" ? "zaakceptowano" : "do zmiany"}
          </span>
        ) : null}
      </div>

      {stage === "scope" ? (
        <>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            <PlanningFact label="Strona" value={proposal.final_canonical_url} />
            <PlanningFact label="Usługa" value={proposal.service_label ?? "Brak dopasowanej usługi"} />
            <PlanningFact label="Intencja" value={proposal.search_intent} />
            <PlanningFact label="Odbiorca" value={proposal.target_reader} />
            <PlanningFact label="Problem" value={proposal.buyer_problem} />
            <PlanningFact label="Moment decyzji" value={proposal.buyer_trigger} />
            <PlanningFact label="CTA" value={proposal.cta_direction} />
            <PlanningFact
              label="Linkowanie wewnętrzne"
              value={proposal.internal_link_directions.join(" · ") || "Brak kierunku linkowania"}
            />
          </dl>
          <SearchDemandSummary demand={proposal.search_demand} />
        </>
      ) : (
        <ol className="mt-4 space-y-3">
          {proposal.sections.map((section, index) => (
            <li key={`${index}-${section.heading}`} className="rounded-md border border-line bg-surface p-3">
              <div className="flex items-start gap-3">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-action text-xs font-bold text-white">
                  {index + 1}
                </span>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-ink">{section.heading}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-700">{section.purpose}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {section.evidence_ids.length} {section.evidence_ids.length === 1 ? "dowód" : "dowodów"}
                  </p>
                  <SectionDemandTerms
                    heading={section.heading}
                    rows={proposal.search_demand.gsc_query_rows}
                  />
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}

      <div className="mt-5 grid gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
        <label className="text-sm font-semibold text-ink">
          Decyzja
          <select
            aria-label="Decyzja planistyczna"
            value={decision}
            onChange={(event) => setDecision(event.target.value as typeof decision)}
            className="mt-2 h-11 w-full rounded-md border border-line bg-white px-3 text-sm font-normal"
          >
            <option value="approved">Akceptuję ten krok</option>
            <option value="needs_changes">Wymaga zmian</option>
          </select>
        </label>
        <label className="text-sm font-semibold text-ink">
          Notatka
          <textarea
            aria-label="Notatka do planu"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Co zaakceptowano albo co trzeba poprawić?"
            className="mt-2 min-h-20 w-full rounded-md border border-line bg-white p-3 text-sm font-normal leading-6"
          />
        </label>
      </div>

      {decision === "approved" ? (
        <label className="mt-3 flex items-start gap-2 text-sm leading-6 text-slate-700">
          <input
            type="checkbox"
            checked={checked}
            onChange={(event) => setChecked(event.target.checked)}
            className="mt-1"
          />
          {stage === "scope"
            ? "Sprawdziłem stronę, usługę, intencję, odbiorcę i CTA."
            : "Sprawdziłem kolejność, cel i dowody każdej sekcji."}
        </label>
      ) : null}

      <button
        type="button"
        disabled={!canSubmit}
        onClick={() =>
          actions.save(
            stage,
            decision,
            notes,
            checked ? [stage === "scope" ? "zakres i CTA" : "kolejność, cel i dowody"] : []
          )
        }
        className="mt-4 inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
      >
        {actions.pending
          ? "Zapisuję decyzję..."
          : decision === "approved"
            ? "Zapisz decyzję i przejdź dalej"
            : "Zapisz uwagi do poprawy"}
      </button>

      {actions.conflict ? (
        <div role="alert" className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700">
          <p className="font-semibold text-wait">Plan zmienił się na serwerze</p>
          <p className="mt-1">Twoja notatka pozostała w formularzu. {actions.conflict.detail}</p>
          <button type="button" onClick={actions.refresh} className="mt-2 font-semibold text-action underline">
            Odśwież aktualny plan
          </button>
        </div>
      ) : null}
      {actions.error ? (
        <p role="alert" className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          Nie udało się zapisać decyzji. WILQ nie zmienił planu.
        </p>
      ) : null}
    </section>
  );
}

function SearchDemandSummary({
  demand
}: {
  demand: ContentPlanningWorkspace["proposal"]["search_demand"];
}) {
  return (
    <div className="mt-4 rounded-md border border-line bg-surface p-3">
      <h3 className="text-sm font-semibold text-ink">Popyt z wyszukiwarki dla tej strony</h3>
      {demand.gsc_query_rows.length ? (
        <ul className="mt-2 grid gap-2 md:grid-cols-2">
          {demand.gsc_query_rows.slice(0, 4).map((row) => (
            <li key={`${row.page}-${row.term}`} className="rounded-md bg-white p-3 text-sm">
              <p className="font-semibold text-ink">{row.term}</p>
              <p className="mt-1 text-xs text-slate-600">
                {formatDemandMetrics(row)} · {demandPeriodLabel(row.period)} · {row.freshness === "fresh" ? "świeże" : "wymaga odświeżenia"}
              </p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm leading-6 text-slate-700">{demand.safe_next_step}</p>
      )}
      <p className="mt-2 text-xs text-slate-500">
        Ads i Keyword Planner: {demand.optional_ads_status === "exact_rows_available" ? "ścisłe dopasowanie dostępne" : "brak ścisłego mapowania do strony i usługi — nie używamy"}.
      </p>
    </div>
  );
}

function SectionDemandTerms({
  heading,
  rows
}: {
  heading: string;
  rows: ContentPlanningWorkspace["proposal"]["search_demand"]["gsc_query_rows"];
}) {
  const terms = rows.filter((row) => row.section_headings.includes(heading)).slice(0, 3);
  if (!terms.length) return null;
  return (
    <p className="mt-2 text-xs leading-5 text-slate-600">
      Zapytania GSC: {terms.map((row) => row.term).join(" · ")}
    </p>
  );
}

function formatDemandMetrics(
  row: ContentPlanningWorkspace["proposal"]["search_demand"]["gsc_query_rows"][number]
) {
  const metrics = [
    row.impressions === null ? null : `${row.impressions} wyśw.`,
    row.clicks === null ? null : `${row.clicks} klik.`,
    row.ctr === null ? null : `CTR ${(row.ctr * 100).toFixed(1)}%`,
    row.average_position === null ? null : `poz. ${row.average_position.toFixed(1)}`
  ].filter(Boolean);
  return metrics.join(" · ") || "Brak metryk liczbowych";
}

function demandPeriodLabel(period: string) {
  const labels: Record<string, string> = {
    connector_refresh: "ostatni odczyt",
    last_28_days: "ostatnie 28 dni",
    search_term_safety_90d: "ostatnie 90 dni",
    keyword_planner: "Keyword Planner"
  };
  return labels[period] ?? "okres ze źródła";
}

function PlanningFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-surface p-3">
      <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-sm leading-6 text-ink">{value}</dd>
    </div>
  );
}
