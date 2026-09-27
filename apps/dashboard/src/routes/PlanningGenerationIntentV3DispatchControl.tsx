import { useMutation } from "@tanstack/react-query";

import { dispatchPlanningGenerationIntentV3, type ActionObject } from "../lib/api";

export function PlanningGenerationIntentV3DispatchControl({ action }: { action: ActionObject }) {
  const dispatch = useMutation({
    mutationFn: () => dispatchPlanningGenerationIntentV3(action.id)
  });

  if (action.status !== "applied") {
    return (
      <p className="mt-6 text-sm text-slate-700">
        Najpierw zatwierdź lokalny zamiar planowania, aby uruchomić planowanie.
      </p>
    );
  }

  return (
    <section className="mt-6 rounded-md border border-line bg-white p-4">
      <p className="text-sm leading-5 text-slate-700">
        Uruchomienie sprawdza zatwierdzony lokalny zamiar przed przekazaniem planowania.
      </p>
      <button
        type="button"
        onClick={() => dispatch.mutate()}
        disabled={dispatch.isPending}
        className="mt-3 rounded-md bg-action px-3 py-2 font-semibold text-white disabled:opacity-60"
      >
        Uruchom planowanie z zatwierdzonego zamiaru
      </button>
      {dispatch.data?.status === "accepted" ? (
        <p className="mt-3 text-sm text-action" role="status">
          Planowanie przyjęte. Status propozycji: {dispatch.data.proposal_status ?? "brak"}.
          {dispatch.data.intent_receipt_id ? ` Receipt zamiaru: ${dispatch.data.intent_receipt_id}.` : ""}
        </p>
      ) : null}
      {dispatch.data?.status === "blocked" ? (
        <p className="mt-3 text-sm text-risk" role="alert">
          {dispatch.data.blocker
            ? `${dispatch.data.blocker.safe_next_step} Odpowiedzialny: ${dispatch.data.blocker.owner}.`
            : dispatch.data.safe_next_step}
        </p>
      ) : null}
      {dispatch.isError ? (
        <p className="mt-3 text-sm text-risk" role="alert">
          Nie udało się uruchomić planowania. Spróbuj ponownie.
        </p>
      ) : null}
    </section>
  );
}
