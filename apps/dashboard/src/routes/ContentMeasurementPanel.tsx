import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  postContentWorkItemLearningProposal,
  postContentWorkItemMeasurementOutcome,
  postContentWorkItemMeasurementWindow,
  type ContentPublicDeploymentReadResponse
} from "../lib/api";

export function ContentMeasurementPanel({
  workItemId,
  revisionId,
  state
}: {
  workItemId: string;
  revisionId: string;
  state: ContentPublicDeploymentReadResponse;
}) {
  const queryClient = useQueryClient();
  const refresh = () => void queryClient.invalidateQueries({
    queryKey: [
      "content-workflow",
      "work-item",
      workItemId,
      "draft-revisions",
      revisionId,
      "public-deployment"
    ]
  });
  const createWindow = useMutation({
    mutationFn: () => postContentWorkItemMeasurementWindow({
      work_item_id: workItemId,
      revision_id: revisionId
    }),
    onSuccess: refresh
  });
  const outcome = useMutation({
    mutationFn: () => {
      if (!state.measurement_window) throw new Error("Brakuje okna pomiaru.");
      return postContentWorkItemMeasurementOutcome({
        work_item_id: workItemId,
        measurement_window_id: state.measurement_window.id
      });
    },
    onSuccess: refresh
  });
  const learning = useMutation({
    mutationFn: () => {
      if (!state.measurement_window) throw new Error("Brakuje okna pomiaru.");
      return postContentWorkItemLearningProposal({
        work_item_id: workItemId,
        measurement_window_id: state.measurement_window.id
      });
    },
    onSuccess: refresh
  });
  const window = state.measurement_window;
  const outcomeReadyForLearning = Boolean(
    state.measurement_outcome
    && !["not_ready", "insufficient_data"].includes(state.measurement_outcome.status)
  );

  return (
    <section className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" data-testid="content-measurement-panel">
      <p className="font-semibold text-ink">Pomiar i wnioski</p>
      {!window ? (
        <>
          <p className="mt-2 leading-6">
            Po potwierdzeniu wdrożenia WILQ może wyznaczyć lokalne okno pomiaru dla tej dokładnej wersji. Nie ocenia jeszcze wyniku ani nie uruchamia żadnego źródła danych.
          </p>
          <button
            type="button"
            className="mt-3 w-full rounded-md bg-action px-3 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={createWindow.isPending}
            onClick={() => createWindow.mutate()}
          >
            {createWindow.isPending ? "Tworzę okno pomiaru…" : "Utwórz okno pomiaru"}
          </button>
          {createWindow.data?.measurement_window_result.blockers.map((blocker) => (
            <p key={blocker.code} className="mt-3 leading-6 text-wait">{blocker.reason}</p>
          ))}
          {createWindow.isError ? <p className="mt-3 font-semibold text-wait">{createWindow.error.message}</p> : null}
        </>
      ) : (
        <>
          <p className="mt-2 leading-6">Okno obserwacji trwa do {formatDate(window.observation_period.end)}.</p>
          {!state.measurement_outcome ? (
            state.outcome_allowed ? (
              <button
                type="button"
                className="mt-3 w-full rounded-md bg-action px-3 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
                disabled={outcome.isPending}
                onClick={() => outcome.mutate()}
              >
                {outcome.isPending ? "Oceniam dane…" : "Oceń dane w oknie pomiaru"}
              </button>
            ) : (
              <p className="mt-3 leading-6 text-slate-600">
                WILQ nie pozwala jeszcze oceniać wyniku. Wróć po {formatDate(window.earliest_verdict_date)}.
              </p>
            )
          ) : (
            <section className="mt-3 rounded-lg bg-slate-50 p-3">
              <p className="font-semibold text-ink">{state.measurement_outcome.status_label}</p>
              <p className="mt-2 leading-6">{state.measurement_outcome.conclusion}</p>
              <p className="mt-2 leading-6 text-slate-600">{state.measurement_outcome.safe_next_step}</p>
              {outcomeReadyForLearning && !state.learning_proposal ? (
                <button
                  type="button"
                  className="mt-3 w-full rounded-md border border-action px-3 py-2 font-semibold text-action disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={learning.isPending}
                  onClick={() => learning.mutate()}
                >
                  {learning.isPending ? "Przygotowuję wniosek…" : "Przygotuj wniosek do review"}
                </button>
              ) : null}
              {state.learning_proposal ? (
                <p className="mt-3 leading-6 text-slate-600">
                  Wniosek jest zapisany do osobnego review; nie zmienia automatycznie wiedzy ani kolejki.
                </p>
              ) : null}
            </section>
          )}
          {outcome.isError ? <p className="mt-3 font-semibold text-wait">{outcome.error.message}</p> : null}
          {learning.isError ? <p className="mt-3 font-semibold text-wait">{learning.error.message}</p> : null}
        </>
      )}
      <p className="mt-3 text-xs leading-5 text-slate-600">
        Wynik i ewentualny wniosek pozostają powiązane z tym potwierdzonym wdrożeniem. Nie są automatycznym claimem SEO ani zmianą publikacji.
      </p>
    </section>
  );
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("pl-PL");
}
