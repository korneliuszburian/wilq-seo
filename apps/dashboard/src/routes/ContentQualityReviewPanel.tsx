import { ShieldCheck } from "lucide-react";

import type { ContentWorkItemQualityReviewResponse } from "../lib/api";

export function ContentQualityReviewPanel({
  review,
  safetyText
}: {
  review: ContentWorkItemQualityReviewResponse["quality_review"] | null;
  safetyText: string;
}) {
  const firstFinding = review?.blockers[0] ?? review?.findings[0] ?? null;
  return (
    <section className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-md border border-line bg-surface p-2 text-action"><ShieldCheck aria-hidden="true" size={18} /></div>
        <div>
          <h2 className="text-sm font-semibold text-ink">Ocena jakości szkicu</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">{safetyText}</p>
          {review ? <div className="mt-3 space-y-3 text-sm text-slate-700">
            <div className="rounded-md border border-line bg-surface p-3"><div className="text-xs uppercase tracking-normal text-slate-500">Następny krok</div><div className="mt-1 font-medium text-ink">{review.safe_next_step}</div></div>
            {firstFinding ? <div className="rounded-md border border-line bg-surface p-3"><div className="font-semibold text-ink">{firstFinding.label}</div><p className="mt-2 leading-6">{firstFinding.reason}</p><p className="mt-2 text-xs text-slate-500">{firstFinding.next_step}</p></div> : null}
            <div className="grid gap-2 sm:grid-cols-2">{[review.evidence_coverage, review.claim_safety, review.cta_quality].map((dimension) => <div key={dimension.label} className="rounded-md border border-line bg-surface p-3"><div className="font-semibold text-ink">{dimension.label}</div><p className="mt-1 text-xs leading-5 text-slate-500">{dimension.reason}</p></div>)}</div>
          </div> : null}
        </div>
      </div>
    </section>
  );
}
