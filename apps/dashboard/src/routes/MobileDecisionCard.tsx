import type { ContentWorkItemQueueCandidate, ContentWorkItemQueueResponse } from "../lib/api";

type MobileDecisionCardProps = {
  candidate: ContentWorkItemQueueCandidate | null;
  publicUrl: string;
  topic: string;
  queue: ContentWorkItemQueueResponse;
  onOpenDetails: () => void;
};

export function MobileDecisionCard({ candidate, publicUrl, topic, queue, onOpenDetails }: MobileDecisionCardProps) {
  const blocker = queue.blockers[0] ?? candidate?.blockers[0] ?? null;
  const blockerLabel = blocker?.label ?? queue.freshness_assessment.state_label;
  const blockerReason = blocker?.reason ?? queue.freshness_assessment.summary;
  const decision = candidate?.recommended_mode_label ?? "Wymaga sprawdzenia";

  return (
    <section className="mb-4 rounded-md border border-action/25 bg-white p-4 shadow-sm sm:hidden" aria-label="Decyzja mobilna">
      <div className="text-xs font-semibold uppercase tracking-normal text-action">Decyzja teraz</div>
      <h2 className="mt-1 text-lg font-semibold leading-6 text-ink">{topic}</h2>
      {publicUrl ? <p className="mt-1 truncate text-xs font-medium text-action">{publicUrl}</p> : null}
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="text-sm font-semibold text-ink">{decision}</span>
        <span className="rounded-md bg-wait/10 px-2 py-1 text-xs font-semibold text-wait">{blockerLabel}</span>
      </div>
      <p className="mt-2 line-clamp-3 text-sm leading-5 text-slate-700">{blockerReason}</p>
      <button type="button" onClick={onOpenDetails} className="mt-3 inline-flex h-10 w-full items-center justify-center rounded-md bg-action px-3 text-sm font-semibold text-white">
        Otwórz decyzję i dowody
      </button>
    </section>
  );
}
