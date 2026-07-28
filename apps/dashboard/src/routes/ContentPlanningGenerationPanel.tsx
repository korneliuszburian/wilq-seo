import { useMutation, useQueryClient } from "@tanstack/react-query";

import { postContentWorkItemPlanningProposal } from "../lib/api";
import { useContentPlanningProposal } from "./contentWorkflowQueries";

/** Owns only the state before a proposal exists. The proposal itself is rendered once below. */
export function ContentPlanningGenerationPanel({ workItemId }: { workItemId: string }) {
  const queryClient = useQueryClient();
  const queryKey = ["content-workflow", "work-item", workItemId, "planning-proposal"];
  const status = useContentPlanningProposal(workItemId);
  const generation = useMutation({
    mutationFn: () => {
      const planningInputDigest = status.data?.planning_input_digest;
      const serviceCardId = status.data?.service_card_id;
      if (!planningInputDigest || !serviceCardId) throw new Error("Planning input is not ready.");
      return postContentWorkItemPlanningProposal({
        service_card_id: serviceCardId,
        expected_planning_input_digest: planningInputDigest,
        operator_hint: "",
        requested_by: "wilku"
      }, workItemId);
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey }),
        queryClient.invalidateQueries({ queryKey: ["content-workflow", "work-item", workItemId], exact: true })
      ]);
    }
  });

  if (status.isLoading) return <PlanningState>Sprawdzam, czy można przygotować strukturę…</PlanningState>;
  if (status.error || !status.data) return <PlanningState tone="error">Nie udało się odczytać gotowości planu. Odśwież widok przed kolejną próbą.</PlanningState>;

  const state = generation.data ?? status.data;
  const hasProposal = ["created", "idempotent", "ready"].includes(state.status) && Boolean(state.proposal);
  if (hasProposal) return null;

  const blocker = state.blockers[0] ?? null;
  const input = state.input_summary;
  const inputReady = Boolean(
    input &&
      input.inventory_status === "available" &&
      input.content_inventory_status === "available" &&
      !input.source_assessments.some((source) => source.status === "stale" || source.status === "blocked")
  );
  const canGenerate = Boolean(
    state.service_card_id &&
      state.planning_input_digest &&
      inputReady &&
      (["not_generated", "failed"].includes(state.status) ||
        (state.status === "stale" && state.blockers.every((item) => item.code === "stale_input")))
  );

  return <section aria-labelledby="content-planning-generation-title" className="rounded-md border border-line bg-white p-4 shadow-sm" data-testid="content-planning-generation">
    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Następny krok</p>
    <h2 id="content-planning-generation-title" className="mt-1 text-lg font-semibold text-ink">{planningHeadline(state.status)}</h2>
    <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">{blocker?.reason ?? "WILQ użyje aktualnej strony, wybranej usługi i zapisanych źródeł. Przygotowanie struktury nie zmienia WordPressa."}</p>
    {canGenerate ? <button type="button" disabled={generation.isPending} onClick={() => generation.mutate()} className="mt-4 inline-flex h-11 items-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60">
      {generation.isPending ? "Przygotowuję strukturę…" : state.status === "failed" ? "Spróbuj ponownie" : state.status === "stale" ? "Przygotuj aktualną strukturę" : "Przygotuj strukturę"}
    </button> : null}
    {state.status === "generating" ? <p aria-live="polite" className="mt-4 rounded-md border border-action/20 bg-action/5 p-3 text-sm text-slate-700">Struktura jest przygotowywana. Ten widok odświeży się po zakończeniu i nie uruchomi drugiej wersji dla tych samych danych.</p> : null}
    {blocker ? <p className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-sm text-slate-700"><span className="font-semibold text-wait">Co wymaga uwagi: </span>{blocker.label}. {blocker.next_step}</p> : null}
    {generation.error ? <p role="alert" className="mt-3 text-sm text-danger">Nie udało się przygotować struktury. Nic nie zostało zmienione.</p> : null}
    <p className="mt-3 text-xs leading-5 text-slate-500">Otwarcie tego widoku niczego nie generuje. Po utworzeniu struktury zobaczysz jeden szkic do sprawdzenia.</p>
  </section>;
}

function PlanningState({ children, tone = "normal" }: { children: string; tone?: "normal" | "error" }) {
  return <section className={`rounded-md border p-4 shadow-sm ${tone === "error" ? "border-danger/30 bg-danger/5 text-danger" : "border-line bg-white text-slate-600"}`}><p className="text-sm">{children}</p></section>;
}

function planningHeadline(status: string) {
  if (status === "generating") return "Przygotowuję strukturę tekstu";
  if (status === "stale") return "Struktura wymaga odświeżenia";
  if (status === "blocked") return "Nie można jeszcze przygotować struktury";
  if (status === "failed") return "Nie udało się przygotować struktury";
  return "Przygotuj strukturę tekstu";
}
