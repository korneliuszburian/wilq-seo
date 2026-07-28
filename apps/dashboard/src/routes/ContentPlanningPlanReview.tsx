import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getContentWorkItemInitialDraft,
  postContentWorkItemInitialDraft,
  saveContentWorkItemPlanningReview,
  type ContentInitialDraftResponse,
  type ContentPlanningReviewConflict
} from "../lib/api";
import { useContentPlanningProposal } from "./contentWorkflowQueries";

export function ContentPlanningPlanReview({ workItemId }: { workItemId: string }) {
  const queryClient = useQueryClient();
  const planningStatus = useContentPlanningProposal(workItemId);
  const [conflict, setConflict] = useState<ContentPlanningReviewConflict | null>(null);
  const [showChanges, setShowChanges] = useState(false);
  const [notes, setNotes] = useState("");
  const [initialDraft, setInitialDraft] = useState<ContentInitialDraftResponse | null>(null);
  const initialDraftStatus = useQuery({
    queryKey: ["content-workflow", "work-item", workItemId, "initial-draft"],
    queryFn: () => getContentWorkItemInitialDraft(workItemId),
    enabled: initialDraft?.status === "generating",
    refetchInterval: (query) => query.state.data?.status === "generating" ? 1500 : false
  });
  const prepareText = useMutation({
    mutationFn: async ({
      expectedPlanningDigest,
      planningInputDigest,
      proposalId,
      serviceCardId
    }: {
      expectedPlanningDigest: string;
      planningInputDigest: string;
      proposalId: string;
      serviceCardId: string | null;
    }) => {
      const review = await saveContentWorkItemPlanningReview(
        {
          stage: "scope",
          expected_planning_digest: expectedPlanningDigest,
          service_card_id: serviceCardId,
          decision: "approved",
          reviewed_by: "wilku",
          checked_items: ["plan, struktura i źródła"],
          notes: ""
        },
        workItemId
      );
      if ("code" in review) return { review, initialDraft: null };
      return {
        review,
        initialDraft: await postContentWorkItemInitialDraft(
          {
            expected_proposal_id: proposalId,
            expected_planning_digest: expectedPlanningDigest,
            expected_planning_input_digest: planningInputDigest,
            requested_by: "wilku"
          },
          workItemId
        )
      };
    },
    onSuccess: async (result) => {
      if ("code" in result.review) {
        setConflict(result.review);
        return;
      }
      setConflict(null);
      setInitialDraft(result.initialDraft);
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
  const requestChanges = useMutation({
    mutationFn: ({ expectedPlanningDigest, serviceCardId }: { expectedPlanningDigest: string; serviceCardId: string | null }) =>
      saveContentWorkItemPlanningReview({
        stage: "scope",
        expected_planning_digest: expectedPlanningDigest,
        service_card_id: serviceCardId,
        decision: "needs_changes",
        reviewed_by: "wilku",
        checked_items: [],
        notes: notes.trim()
      }, workItemId),
    onSuccess: async (result) => {
      if ("code" in result) {
        setConflict(result);
        return;
      }
      setConflict(null);
      await queryClient.invalidateQueries({ queryKey: ["content-workflow", "work-item", workItemId, "planning-proposal"] });
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

  const planning = planningStatus.data?.planning_workspace;
  const planningInputDigest = planningStatus.data?.planning_input_digest;
  const proposalId = planning?.proposal.proposal_id;
  if (!planning || !planningInputDigest || !proposalId) return null;

  return (
    <>
      {conflict ? (
        <aside
          role="alert"
          className="rounded-md border border-wait/30 bg-wait/10 p-3 text-sm leading-6 text-slate-700"
        >
          <p className="font-semibold text-wait">Plan zmienił się na serwerze</p>
          <p className="mt-1">{conflict.safe_next_step}</p>
          <button
            type="button"
            onClick={() => {
              setConflict(null);
              void planningStatus.refetch();
            }}
            className="mt-2 font-semibold text-action underline"
          >
            Odśwież aktualny plan
          </button>
        </aside>
      ) : null}
      <section
        aria-labelledby="generated-plan-review-title"
        className="rounded-md border border-line bg-white p-4 shadow-sm"
        data-testid="generated-plan-review"
      >
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Plan treści</p>
        <h2 id="generated-plan-review-title" className="mt-1 text-lg font-semibold text-ink">
          Sprawdź wygenerowany plan
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">
          WILQ wygenerował plan z aktualnych źródeł i wybranej usługi. Jeśli plan jest OK, od razu przygotuj pełny tekst.
        </p>
        <div className="mt-4 grid gap-3 rounded-md border border-line bg-surface p-3 text-sm sm:grid-cols-3">
          <PlanFact label="Intencja" value={planning.proposal.search_intent} />
          <PlanFact label="Odbiorca" value={planning.proposal.target_reader} />
          <PlanFact label="Następny krok" value={planning.proposal.cta_direction} />
        </div>
        <ol className="mt-4 space-y-2" aria-label="Sekcje wygenerowanego planu">
          {planning.proposal.sections.map((section, index) => (
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
              expectedPlanningDigest: planning.proposal.planning_digest,
              planningInputDigest,
              proposalId,
              serviceCardId: planning.proposal.service_card_id
            })}
            className="inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {prepareText.isPending ? "Przygotowuję tekst…" : currentInitialDraft?.status === "generating" ? "Tekst jest przygotowywany…" : "Przygotuj pełny tekst"}
          </button>
          <button type="button" className="text-sm font-semibold text-action underline" onClick={() => setShowChanges((value) => !value)}>
            {showChanges ? "Anuluj uwagi" : "Plan wymaga zmian"}
          </button>
        </div>
        {showChanges ? <div className="mt-4 rounded-md border border-line bg-surface p-3">
          <label className="block text-sm font-semibold text-ink">Co poprawić w planie?
            <textarea aria-label="Notatka do planu" value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-2 min-h-20 w-full rounded-md border border-line bg-white p-3 text-sm font-normal leading-6" />
          </label>
          <button type="button" disabled={requestChanges.isPending || !notes.trim()} onClick={() => requestChanges.mutate({ expectedPlanningDigest: planning.proposal.planning_digest, serviceCardId: planning.proposal.service_card_id })} className="mt-3 inline-flex h-10 items-center rounded-md border border-action/30 px-3 text-sm font-semibold text-action disabled:opacity-60">
            {requestChanges.isPending ? "Zapisuję uwagi…" : "Zapisz uwagi do planu"}
          </button>
        </div> : null}
        {currentInitialDraft ? <p aria-live="polite" className="mt-3 rounded-md border border-action/20 bg-action/5 p-3 text-sm text-slate-700">
          {currentInitialDraft.status === "generating" ? "Pełny tekst jest przygotowywany. Ten widok odświeży się po zakończeniu." : currentInitialDraft.safe_next_step}
        </p> : null}
        {prepareText.error || requestChanges.error ? <p role="alert" className="mt-3 text-sm text-danger">Nie udało się zapisać decyzji ani uruchomić tekstu. Plan pozostał bez zmian.</p> : null}
      </section>
    </>
  );
}

function PlanFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p><p className="mt-1 text-sm leading-6 text-ink">{value}</p></div>;
}
