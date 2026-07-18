import type {
  ContentWorkItemQueueCandidate,
  ContentWorkItemQueueResponse
} from "../lib/api";
import { ContentWorkflowHeader } from "./ContentWorkflowHeader";

export function ContentFreshnessBanner({
  assessment
}: {
  assessment: ContentWorkItemQueueResponse["freshness_assessment"];
}) {
  if (!assessment.requires_refresh) return null;
  return (
    <section className="mb-4 rounded-md border border-wait/30 bg-wait/10 p-4" role="status">
      <h2 className="text-sm font-semibold text-wait">
        Źródła treści: {assessment.state_label}
      </h2>
      <p className="mt-2 hidden text-sm leading-6 text-slate-700 sm:block">{assessment.summary}</p>
      <p className="mt-2 line-clamp-3 text-xs font-semibold leading-5 text-ink sm:text-sm sm:leading-6">
        Następny bezpieczny krok: {assessment.next_step}
      </p>
    </section>
  );
}

export function ContentWorkflowError() {
  return <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8"><div className="rounded-md border border-wait/30 bg-wait/10 p-4 text-sm text-wait">Nie udało się odczytać workflow treści z WILQ. Nie pokazujemy decyzji bez kontraktów API.</div></main>;
}

export function ContentWorkflowEmptyQueue({ queue }: { queue: ContentWorkItemQueueResponse }) {
  return <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8"><ContentWorkflowHeader topic="Kolejka treści" /><section className="rounded-md border border-wait/30 bg-wait/10 p-4"><h2 className="text-sm font-semibold uppercase tracking-normal text-wait">Brak propozycji do pracy nad treścią</h2><p className="mt-2 text-sm leading-6 text-slate-700">{queue.operator_summary}</p></section></main>;
}

export function ContentWorkflowSelectedLoading({
  assessment,
  candidate,
  error = false
}: {
  assessment: ContentWorkItemQueueResponse["freshness_assessment"];
  candidate: ContentWorkItemQueueCandidate;
  error?: boolean;
}) {
  return (
    <main className="w-full px-4 py-5 lg:px-7 2xl:px-8">
      <ContentWorkflowHeader topic={candidate.title} />
      <ContentFreshnessBanner assessment={assessment} />
      <section className="rounded-md border border-line bg-white p-4 shadow-sm" aria-live="polite">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
              Wybrany temat
            </p>
            <h1 className="mt-1 text-2xl font-semibold text-ink">{candidate.title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{candidate.reason}</p>
          </div>
          <span className="rounded-md border border-action/30 bg-action/10 px-3 py-2 text-xs font-semibold text-action">
            {candidate.recommended_mode_label}
          </span>
        </div>
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-md border border-line bg-surface p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">Dowody i źródła</div>
            <p className="mt-1 text-slate-700">
              {candidate.evidence_ids.length} dowodów · {candidate.source_connector_labels.join(", ") || "brak źródeł"}
            </p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">Następny bezpieczny krok</div>
            <p className="mt-1 text-slate-700">{candidate.safe_next_step}</p>
          </div>
        </div>
        {candidate.search_metrics ? (
          <div className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-sm" data-testid="content-queue-metrics">
            <div className="text-xs font-semibold uppercase tracking-normal text-action">Co już wiemy z danych</div>
            <p className="mt-1 text-slate-700">{queueMetricSummary(candidate)}</p>
            <p className="mt-1 text-xs text-slate-600">To aktualny punkt odniesienia; trend pokażemy tylko przy dwóch porównywalnych okresach.</p>
          </div>
        ) : null}
        <div className="mt-4 rounded-md border border-line bg-white px-3 py-3 text-sm text-slate-600">
          <p className="font-semibold text-ink">
            {error ? "Nie udało się odczytać szczegółów workflow" : "Ładowanie szczegółów workflow"}
          </p>
          <p className="mt-1">
            {error
              ? "Kolejka pozostaje widoczna. Spróbuj odświeżyć szczegóły, gdy API będzie dostępne."
              : "Decyzja z kolejki jest już dostępna; szczegóły źródeł i etapów doładują się poniżej."}
          </p>
        </div>
      </section>
    </main>
  );
}

function queueMetricSummary(candidate: ContentWorkItemQueueCandidate): string {
  const metrics = candidate.search_metrics;
  if (!metrics) return "Brakuje świeżych danych dla tej strony.";
  const values = [`${metrics.impressions ?? 0} wyświetleń`, `${metrics.clicks ?? 0} kliknięć`];
  if (metrics.ctr !== null && metrics.ctr !== undefined) values.push(`CTR ${(metrics.ctr * 100).toFixed(2)}%`);
  if (metrics.primary_query) values.push(`zapytanie: „${metrics.primary_query}”`);
  return values.join(" · ");
}
