import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  saveContentWorkItemPlanningReview,
  type ContentPlanningReviewConflict
} from "../lib/api";
import { useContentPlanningProposal } from "./contentWorkflowQueries";

export function ContentPlanningPlanReview({ workItemId }: { workItemId: string }) {
  const queryClient = useQueryClient();
  const planningStatus = useContentPlanningProposal(workItemId);
  const [conflict, setConflict] = useState<ContentPlanningReviewConflict | null>(null);
  const [decision, setDecision] = useState<"approved" | "needs_changes">("approved");
  const [notes, setNotes] = useState("");
  const review = useMutation({
    mutationFn: ({
      decision,
      notes,
      checkedItems,
      expectedPlanningDigest,
      serviceCardId
    }: {
      decision: "approved" | "needs_changes";
      notes: string;
      checkedItems: string[];
      expectedPlanningDigest: string;
      serviceCardId: string | null;
    }) =>
      saveContentWorkItemPlanningReview(
        {
          stage: "scope",
          expected_planning_digest: expectedPlanningDigest,
          service_card_id: serviceCardId,
          decision,
          reviewed_by: "wilku",
          checked_items: checkedItems,
          notes
        },
        workItemId
      ),
    onSuccess: async (result) => {
      if ("code" in result) {
        setConflict(result);
        return;
      }
      setConflict(null);
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

  const planning = planningStatus.data?.planning_workspace;
  if (!planning) return null;

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
          WILQ wygenerował plan z aktualnych źródeł i wybranej usługi. Dopiero ta decyzja otwiera przygotowanie pełnego tekstu.
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
        <div className="mt-5 grid gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
          <label className="text-sm font-semibold text-ink">
            Decyzja o planie
            <select aria-label="Decyzja o planie" value={decision} onChange={(event) => setDecision(event.target.value as typeof decision)} className="mt-2 h-11 w-full rounded-md border border-line bg-white px-3 text-sm font-normal">
              <option value="approved">Zatwierdzam plan</option>
              <option value="needs_changes">Plan wymaga zmian</option>
            </select>
          </label>
          <label className="text-sm font-semibold text-ink">
            Notatka{decision === "approved" ? " (opcjonalna)" : ""}
            <textarea aria-label="Notatka do planu" value={notes} onChange={(event) => setNotes(event.target.value)} className="mt-2 min-h-20 w-full rounded-md border border-line bg-white p-3 text-sm font-normal leading-6" />
          </label>
        </div>
        <button
          type="button"
          disabled={review.isPending || (decision === "needs_changes" && !notes.trim())}
          onClick={() => review.mutate({
            decision,
            notes,
            checkedItems: ["plan, struktura i źródła"],
            expectedPlanningDigest: planning.proposal.planning_digest,
            serviceCardId: planning.proposal.service_card_id
          })}
          className="mt-4 inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {review.isPending ? "Zapisuję decyzję..." : decision === "approved" ? "Zatwierdź plan do tekstu" : "Zapisz uwagi do poprawy"}
        </button>
        {review.error ? <p role="alert" className="mt-3 text-sm text-danger">Nie udało się zapisać decyzji. Plan nie został zmieniony.</p> : null}
      </section>
    </>
  );
}

function PlanFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p><p className="mt-1 text-sm leading-6 text-ink">{value}</p></div>;
}
