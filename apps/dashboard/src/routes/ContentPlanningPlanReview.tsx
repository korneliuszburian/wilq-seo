import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getContentWorkItemInitialDraft,
  postContentWorkItemInitialDraft,
  type ContentInitialDraftResponse
} from "../lib/api";
import { useContentPlanningProposal } from "./contentWorkflowQueries";

export function ContentPlanningPlanReview({ workItemId }: { workItemId: string }) {
  const queryClient = useQueryClient();
  const planningStatus = useContentPlanningProposal(workItemId);
  const [initialDraft, setInitialDraft] = useState<ContentInitialDraftResponse | null>(null);
  const initialDraftStatus = useQuery({
    queryKey: ["content-workflow", "work-item", workItemId, "initial-draft"],
    queryFn: () => getContentWorkItemInitialDraft(workItemId),
    enabled: initialDraft?.status === "generating",
    refetchInterval: (query) => query.state.data?.status === "generating" ? 1500 : false
  });
  const prepareText = useMutation({
    mutationFn: ({
      expectedPlanningDigest,
      planningInputDigest,
      proposalId
    }: {
      expectedPlanningDigest: string;
      planningInputDigest: string;
      proposalId: string;
    }) => postContentWorkItemInitialDraft(
      {
        expected_proposal_id: proposalId,
        expected_planning_digest: expectedPlanningDigest,
        expected_planning_input_digest: planningInputDigest,
        requested_by: "wilku"
      },
      workItemId
    ),
    onSuccess: async (result) => {
      setInitialDraft(result);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["content-workflow", "work-item", workItemId, "planning-proposal"]
        }),
        queryClient.invalidateQueries({
          queryKey: ["content-workflow", "work-item", workItemId, "selected-workspace"]
        })
      ]);
    }
  });
  const currentInitialDraft = initialDraftStatus.data ?? initialDraft;
  useEffect(() => {
    if (currentInitialDraft?.status === "created") {
      void queryClient.invalidateQueries({
        queryKey: ["content-workflow", "work-item", workItemId, "selected-workspace"]
      });
    }
  }, [currentInitialDraft?.status, queryClient, workItemId]);

  const proposal = planningStatus.data?.proposal;
  const planningInputDigest = planningStatus.data?.planning_input_digest;
  const proposalId = proposal?.proposal_id;
  if (!proposal || !planningInputDigest || !proposalId) return null;

  return (
    <>
      <section
        aria-labelledby="generated-plan-review-title"
        className="rounded-md border border-line bg-white p-4 shadow-sm"
        data-testid="generated-plan-review"
      >
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Plan treści</p>
        <h2 id="generated-plan-review-title" className="mt-1 text-lg font-semibold text-ink">
          Szkic struktury tekstu
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
          WILQ przygotował strukturę z aktualnych źródeł i wybranej usługi. To roboczy szkic; pełny tekst powstanie z dokładnie tej wersji.
        </p>
        <div className="mt-4 grid gap-3 rounded-md border border-line bg-surface p-3 text-sm sm:grid-cols-3">
          <PlanFact label="Intencja" value={proposal.search_intent} />
          <PlanFact label="Odbiorca" value={proposal.target_reader} />
          <PlanFact label="Następny krok" value={proposal.cta_direction} />
        </div>
        <ol className="mt-4 space-y-2" aria-label="Sekcje wygenerowanego planu">
          {proposal.sections.map((section, index) => (
            <li key={`${section.section_id ?? index}-${section.heading}`} className="rounded-md border border-line bg-surface p-3 text-sm">
              <p className="font-semibold text-ink">{index + 1}. {section.heading}</p>
              <p className="mt-1 leading-6 text-slate-700">{section.purpose}</p>
            </li>
          ))}
        </ol>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={prepareText.isPending || currentInitialDraft?.status === "generating"}
            onClick={() => prepareText.mutate({
              expectedPlanningDigest: proposal.planning_digest,
              planningInputDigest,
              proposalId
            })}
            className="inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {prepareText.isPending ? "Przygotowuję tekst…" : currentInitialDraft?.status === "generating" ? "Tekst jest przygotowywany…" : "Przygotuj pełny tekst"}
          </button>
        </div>
        {currentInitialDraft ? <p aria-live="polite" className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-sm text-slate-700">
          {currentInitialDraft.status === "generating" ? "Pełny tekst jest przygotowywany. Ten widok odświeży się po zakończeniu." : currentInitialDraft.safe_next_step}
        </p> : null}
        {prepareText.error ? <p role="alert" className="mt-3 text-sm text-danger">Nie udało się uruchomić tekstu. Odśwież szkic i spróbuj ponownie.</p> : null}
      </section>
    </>
  );
}

function PlanFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p><p className="mt-1 text-sm leading-6 text-ink">{value}</p></div>;
}
