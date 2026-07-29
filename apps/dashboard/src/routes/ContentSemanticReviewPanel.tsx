import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getContentWorkItemSemanticReview } from "../lib/api";
import type { ContentSemanticReviewResponse } from "../lib/api";

export function ContentSemanticReviewPanel({
  workItemId,
  revisionId
}: {
  workItemId: string;
  revisionId: string;
}) {
  const [opened, setOpened] = useState(false);
  const semanticReview = useQuery({
    queryKey: ["content-workflow", "work-item", workItemId, "draft-revisions", revisionId, "semantic-review"],
    queryFn: () => getContentWorkItemSemanticReview(workItemId, revisionId),
    enabled: opened,
    staleTime: 30_000
  });

  return (
    <section className="mt-4 rounded-xl border border-line bg-slate-50 p-4" data-testid="content-semantic-review">
      <p className="text-sm font-semibold text-ink">Wskazówki jakości tekstu</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">
        To pomocniczy odczyt dla tej dokładnej wersji. Nie zmienia tekstu ani nie zastępuje decyzji człowieka.
      </p>
      {!opened ? (
        <button
          type="button"
          className="mt-3 rounded-md border border-action/30 px-3 py-2 text-sm font-semibold text-action"
          onClick={() => setOpened(true)}
        >
          Pokaż wskazówki jakości
        </button>
      ) : null}
      {semanticReview.isLoading ? <p className="mt-3 text-sm text-slate-700">Odczytuję wskazówki dla tej wersji…</p> : null}
      {semanticReview.error ? <p className="mt-3 text-sm font-semibold text-wait">Nie udało się odczytać wskazówek jakości.</p> : null}
      {semanticReview.data ? <SemanticReviewResult response={semanticReview.data} /> : null}
    </section>
  );
}

function SemanticReviewResult({ response }: { response: ContentSemanticReviewResponse }) {
  const review = response.review;
  if (!review) {
    return (
      <div className="mt-3 rounded-lg border border-line bg-white p-3 text-sm leading-6 text-slate-700">
        <p className="font-semibold text-ink">Brak zapisanych wskazówek dla tej wersji.</p>
        <p className="mt-1">{response.safe_next_step}</p>
        {response.blockers.length ? <p className="mt-2">{response.blockers[0]?.reason}</p> : null}
      </div>
    );
  }
  if (review.status === "reviewable") {
    return (
      <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm leading-6 text-emerald-950">
        <p className="font-semibold">Nie znaleziono wskazówek wymagających zmiany.</p>
        <p className="mt-1">{review.safe_next_step}</p>
      </div>
    );
  }
  return (
    <div className="mt-3 space-y-3">
      <p className="text-sm font-semibold text-ink">Zwróć uwagę na {review.findings.length} element{review.findings.length === 1 ? "" : "ów"} przed decyzją.</p>
      <ul className="space-y-2">
        {review.findings.map((finding) => (
          <li key={finding.finding_id} className="rounded-lg border border-wait/30 bg-white p-3 text-sm leading-6 text-slate-700">
            <p className="font-semibold text-ink">{finding.label}</p>
            <p className="mt-1">{finding.reason}</p>
            <p className="mt-2 font-medium text-ink">Co sprawdzić: {finding.instruction}</p>
          </li>
        ))}
      </ul>
      <p className="text-sm text-slate-700">{review.safe_next_step}</p>
    </div>
  );
}
