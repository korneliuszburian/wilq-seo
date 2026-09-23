import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, RefreshCw } from "lucide-react";
import { useState } from "react";

import { type ActionReviewRequest, reviewAction } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { contentDevDraftBinding, type ActionPanelProps } from "./shared";
import {
  materialReviewApprovalAllowed,
  materialReviewCheckedItems,
  materialReviewPageUrl
} from "./materialReviewDecision";

type ActionReviewOutcome = ActionReviewRequest["outcome"];

const ACTION_REVIEW_OPTIONS: Array<{ value: ActionReviewOutcome; label: string }> = [
  { value: "approved_for_prepare", label: "zatwierdzone do przygotowania" },
  { value: "needs_changes", label: "wymaga poprawek" },
  { value: "rejected", label: "odrzucone" },
  { value: "deferred", label: "odłożone" }
];

export function ActionHumanReviewControls({ action }: ActionPanelProps) {
  const wordpressDraft = contentDevDraftBinding(action);
  const materialReview = action.payload.action_type === "content_current_material_review_v2";
  const materialUrl = materialReview ? materialReviewPageUrl(action.payload.material_review_preview) : null;
  const queryClient = useQueryClient();
  const [outcome, setOutcome] = useState<ActionReviewOutcome>("approved_for_prepare");
  const [reviewedFullMaterial, setReviewedFullMaterial] = useState(false);
  const [notes, setNotes] = useState(
    "Przegląd operatora: zapisuję decyzję bez zapisu zmian."
  );
  const reviewMutation = useMutation({
    mutationFn: () =>
      reviewAction(action.id, {
        outcome,
        reviewed_by: "operator_local_dashboard",
        notes: notes.trim(),
        checked_items: materialReview
          ? materialReviewCheckedItems(reviewedFullMaterial)
          : action.review_gate.operator_checklist.slice(0, 8),
        blockers: action.review_gate.apply_blockers.slice(0, 8),
        wordpress_draft: wordpressDraft
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const reviewStatusLabel =
    action.review_gate.last_review_outcome_label ?? action.review_gate.status_label;
  const canSave = notes.trim().length > 0 && !reviewMutation.isPending && (
    !materialReview || materialReviewApprovalAllowed(outcome, reviewedFullMaterial, materialUrl)
  );

  return (
    <div className="mt-3 rounded-md border border-line bg-white p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Wynik przeglądu człowieka
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Zapisuje lokalne zdarzenie audytu. Nie zapisuje zmian w zewnętrznych systemach.
          </p>
        </div>
        <StatusBadge value={action.review_gate.status} label={reviewStatusLabel} />
      </div>
      {action.review_gate.last_review_summary ? (
        <p className="mt-2 rounded-md border border-line bg-slate-50 p-2 leading-5 text-slate-600">
          {action.review_gate.last_review_summary}
        </p>
      ) : null}
      {materialReview ? (
        <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 leading-5 text-slate-700">
          {materialUrl ? (
            <a href={materialUrl} target="_blank" rel="noopener noreferrer" className="font-medium underline">
              Otwórz pełny materiał strony
            </a>
          ) : (
            <p>Brakuje bezpiecznego adresu bieżącej strony do przeglądu.</p>
          )}
          <label className="mt-2 flex items-start gap-2">
            <input
              type="checkbox"
              checked={reviewedFullMaterial}
              onChange={(event) => setReviewedFullMaterial(event.target.checked)}
              disabled={!materialUrl}
              className="mt-1"
            />
            <span>Przeczytałem pełny materiał tej strony i sprawdziłem dokładny URL przed decyzją.</span>
          </label>
        </div>
      ) : null}
      <div className="mt-3 grid gap-3 md:grid-cols-[220px_1fr_auto]">
        <label className="grid gap-1">
          <span className="font-medium text-slate-600">Decyzja</span>
          <select
            value={outcome}
            onChange={(event) => setOutcome(event.target.value as ActionReviewOutcome)}
            className="min-h-9 rounded-md border border-line bg-white px-2 text-xs text-ink"
          >
            {ACTION_REVIEW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          <span className="font-medium text-slate-600">Notatka przeglądu</span>
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            className="min-h-20 rounded-md border border-line bg-white px-2 py-2 text-xs leading-5 text-ink"
          />
        </label>
        <div className="flex items-end">
          <button
            type="button"
            onClick={() => reviewMutation.mutate()}
            disabled={!canSave}
            className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {reviewMutation.isPending ? (
              <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
            ) : (
              <ClipboardCheck aria-hidden="true" size={15} />
            )}
            {reviewMutation.isPending ? "Zapisuję" : "Zapisz przegląd"}
          </button>
        </div>
      </div>
      {reviewMutation.data ? (
        <div className="mt-2 text-slate-600">
          Zapisano sprawdzenie: {reviewMutation.data.audit_event.event_type_label}
        </div>
      ) : null}
      {reviewMutation.error instanceof Error ? (
        <div className="mt-2 text-risk">Błąd przeglądu: {reviewMutation.error.message}</div>
      ) : null}
    </div>
  );
}
