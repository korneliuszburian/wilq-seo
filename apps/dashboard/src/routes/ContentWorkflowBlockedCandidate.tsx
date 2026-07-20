import type { ContentWorkItemQueueResponse } from "../lib/api";
import { ContentWorkflowHeader } from "./ContentWorkflowHeader";
import { ContentFreshnessBanner, type ContentSourceRefreshControl } from "./ContentWorkflowBoundaryStates";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { ContentWorkflowFactTile as FactTile } from "./ContentWorkflowFactTile";
import type { ContentWorkItemQueueCandidate } from "./contentWorkflowQueries";

export function ContentWorkflowBlockedCandidate({
  queue,
  selectedCandidate,
  selectedWorkItemId,
  onSelectWorkItem,
  refresh
}: {
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
  refresh?: ContentSourceRefreshControl;
}) {
  const blocker = selectedCandidate.blockers[0];
  return (
    <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
      <ContentWorkflowHeader topic={selectedCandidate.topic} />
      <ContentFreshnessBanner
        assessment={queue.freshness_assessment}
        refresh={refresh}
        refreshTargetUrl={selectedCandidate.final_canonical_url}
      />
      <ContentCandidateQueuePanel queue={queue} selectedWorkItemId={selectedWorkItemId} onSelectWorkItem={onSelectWorkItem} />
      <section className="mt-6 rounded-md border border-wait/30 bg-wait/10 p-4">
        <h2 className="text-sm font-semibold uppercase tracking-normal text-wait">WILQ blokuje pisanie tego tematu</h2>
        <p className="mt-2 text-sm leading-6 text-slate-700">{blocker?.reason ?? selectedCandidate.reason}</p>
        <p className="mt-2 text-sm font-medium text-ink">Następny bezpieczny krok: {blocker?.next_step ?? selectedCandidate.safe_next_step}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2"><FactTile label="Tryb" value={selectedCandidate.recommended_mode_label} /><FactTile label="Pomiar" value={selectedCandidate.measurement_readiness.label} /></div>
      </section>
    </main>
  );
}
