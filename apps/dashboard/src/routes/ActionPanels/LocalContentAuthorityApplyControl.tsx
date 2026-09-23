import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { applyAction } from "../../lib/api";
import { localAuthorityApplyAllowed } from "./packetReviewDecision";
import type { ActionPanelProps } from "./shared";

export function LocalContentAuthorityApplyControl({ action }: ActionPanelProps) {
  const packet = action.payload.action_type === "content_research_packet_v2_approval";
  const material = action.payload.action_type === "content_current_material_review_v2";
  const supported = (packet || material) && action.payload.local_authority_only === true;
  const queryClient = useQueryClient();
  const [acknowledgedActionId, setAcknowledgedActionId] = useState<string | null>(null);
  const acknowledged = localAuthorityApplyAllowed(action.id, acknowledgedActionId, true);
  const applyMutation = useMutation({
    mutationFn: () => applyAction(action.id, {
      confirm: true,
      confirmed_by: "operator_local_dashboard"
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["content-workflow"] });
    }
  });
  if (!supported) return null;

  const saveLabel = packet ? "Zapisz lokalny receipt pakietu" : "Zapisz lokalny review materiału";
  const reviewLabel = packet ? "pakietu" : "materiału";
  const canApply = localAuthorityApplyAllowed(
    action.id, acknowledgedActionId, action.review_gate.apply_allowed
  ) && !applyMutation.isPending;

  return (
    <section className="mt-3 rounded-md border border-action/30 bg-surface p-3 text-xs">
      <p className="font-semibold uppercase tracking-normal text-ink">Lokalny zapis decyzji</p>
      <p className="mt-1 leading-5 text-slate-700">
        Zapisuje tylko dokładny receipt WILQ. Nie zmienia WordPressa ani nie uruchamia generowania treści.
      </p>
      <label className="mt-3 flex items-start gap-2 leading-5 text-slate-700">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(event) => setAcknowledgedActionId(event.target.checked ? action.id : null)}
          className="mt-0.5"
        />
        <span>Potwierdzam dokładny review {reviewLabel} i lokalny zapis receipt.</span>
      </label>
      {!action.review_gate.apply_allowed ? (
        <p className="mt-2 text-risk">Najpierw dokończ preview, review, confirm i kontrolę efektu.</p>
      ) : null}
      <button
        type="button"
        onClick={() => applyMutation.mutate()}
        disabled={!canApply}
        className="mt-3 rounded-md bg-action px-3 py-2 font-semibold text-white disabled:opacity-60"
      >
        {applyMutation.isPending ? "Zapisuję…" : saveLabel}
      </button>
      {applyMutation.data ? (
        <p className="mt-2 leading-5" role="status">
          {applyMutation.data.applied
            ? "Lokalny receipt zapisany. Bieżąca gotowość treści wymaga osobnego odczytu."
            : applyMutation.data.errors.join(" ")}
        </p>
      ) : null}
      {applyMutation.error instanceof Error ? (
        <p className="mt-2 text-risk" role="alert">
          Zapis zablokowany. Odśwież dokładną akcję i sprawdź jej warunki.
        </p>
      ) : null}
    </section>
  );
}
