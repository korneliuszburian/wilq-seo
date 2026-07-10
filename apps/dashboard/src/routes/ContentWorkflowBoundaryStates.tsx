import type { ContentWorkItemQueueResponse } from "../lib/api";
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
      <p className="mt-2 text-sm leading-6 text-slate-700">{assessment.summary}</p>
      <p className="mt-2 text-sm font-semibold leading-6 text-ink">
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
