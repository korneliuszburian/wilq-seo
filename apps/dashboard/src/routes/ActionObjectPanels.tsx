import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  CheckCircle2,
  ClipboardCheck,
  FileJson,
  RefreshCw,
  ShieldAlert
} from "lucide-react";

import {
  ActionConfirmResult,
  ActionImpactCheckResult,
  ActionObject,
  ActionPreviewResult,
  ActionReviewRequest,
  ActionValidationResult,
  confirmAction,
  impactCheckAction,
  previewAction,
  reviewAction,
  validateAction
} from "../lib/api";
import { MetricFactChips } from "../components/MetricFactChips";
import { BlockerNotice } from "../components/OperatorPrimitives";
import { StatusBadge } from "../components/StatusBadge";
import { LinkedTraceLine, TraceLine } from "../components/TraceLine";
import { adsBlockedClaimLabel, adsMissingReadContractLabel } from "./marketingLabels";

export function ActionObjectFocus({ actions }: { actions: ActionObject[] }) {
  if (actions.length === 0) {
    return (
      <BlockerNotice message="Brak ActionObject dla tego workflow. WILQ może pokazać evidence, ale nie powinien sugerować wykonania bez payload preview." />
    );
  }

  return (
    <section>
      <SectionHeading title="ActionObjecty do walidacji" />
      <div className="grid gap-3 xl:grid-cols-2">
        {actions.map((action) => (
          <article key={action.id} className="rounded-md border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold">{action.title}</h3>
                <p className="mt-1 text-xs uppercase tracking-normal text-slate-500">
                  {action.connector} / {action.mode}
                </p>
              </div>
              <StatusBadge value={action.validation_status} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{action.human_diagnosis}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <StatusBadge value={action.status} />
              <StatusBadge value={action.risk} />
            </div>
            {action.mode !== "apply" ? (
              <div className="mt-3 rounded-md border border-wait/30 bg-wait/10 p-3 text-xs leading-5 text-wait">
                Apply zablokowany: ten ActionObject jest w trybie przygotowania.
                Najpierw walidacja, podgląd payloadu i jawna zgoda operatora.
              </div>
            ) : null}
            <ActionReviewGatePanel action={action} />
            <ActionHumanReviewControls action={action} />
            <ActionPreviewControls action={action} />
            <div className="mt-3 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
              <LinkedTraceLine label="ActionObject" values={[action.id]} kind="actions" />
              <LinkedTraceLine label="Dowody" values={action.evidence_ids} kind="evidence" />
            </div>
            {action.metrics.length > 0 ? <MetricFactChips facts={action.metrics.slice(0, 5)} /> : null}
            <ActionValidationControls action={action} />
            <ActionPayloadPreviewToggle action={action} />
          </article>
        ))}
      </div>
    </section>
  );
}

function ActionPayloadPreviewToggle({ action }: { action: ActionObject }) {
  const [showPayload, setShowPayload] = useState(false);
  const payloadKeys = Object.keys(action.payload);
  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Payload ActionObject
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Domyślnie schowany, żeby karta pokazywała decyzję i bramki review.
            Klucze: {payloadKeys.slice(0, 5).join(", ") || "brak"}
            {payloadKeys.length > 5 ? ` +${payloadKeys.length - 5}` : ""}.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowPayload((current) => !current)}
          className="rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100"
        >
          {showPayload ? "Ukryj payload ActionObject" : "Pokaż payload ActionObject"}
        </button>
      </div>
      {showPayload ? (
        <pre className="mt-3 max-h-56 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      ) : null}
    </div>
  );
}

export function ActionPreviewControls({ action }: { action: ActionObject }) {
  const previewMutation = useMutation({
    mutationFn: () => previewAction(action.id)
  });

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Dry-run preview
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Generuje podgląd payloadu i audit event bez mutacji vendorów.
          </p>
        </div>
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={previewMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {previewMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <FileJson aria-hidden="true" size={15} />
          )}
          {previewMutation.isPending ? "Generuję" : "Generuj preview"}
        </button>
      </div>
      <ActionPreviewResultPanel
        result={previewMutation.data}
        error={previewMutation.error instanceof Error ? previewMutation.error.message : null}
      />
    </div>
  );
}

function ActionPreviewResultPanel({
  result,
  error
}: {
  result?: ActionPreviewResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Preview zablokowany: {error}</div>;
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Preview: <span className="font-semibold">{result.status}</span>
      </div>
      <div>
        Dry-run: {result.dry_run ? "tak" : "nie"}; mutacje:{" "}
        {result.mutation_allowed ? "dopuszczone" : "zablokowane"}
      </div>
      <div>
        Pozycje preview: {result.preview_items.length}/{result.preview_items_total}
        {result.omitted_items > 0 ? `, pominięto ${result.omitted_items}` : ""}
      </div>
      <TraceLine label="Blokady preview" values={result.blockers.map(actionGateLabel)} empty="brak" />
      <div>Audit event: {result.audit_event.event_type}</div>
    </div>
  );
}

export function ActionObjectIdFocus({ actionIds, note }: { actionIds: string[]; note: string }) {
  return (
    <section>
      <SectionHeading title="ActionObjecty do walidacji" />
      <div className="rounded-md border border-line bg-white p-4 text-sm leading-6 text-slate-700">
        <p>{note}</p>
        <div className="mt-3">
          <LinkedTraceLine label="ActionObjecty" values={actionIds} kind="actions" empty="brak" />
        </div>
      </div>
    </section>
  );
}

type ActionReviewOutcome = ActionReviewRequest["outcome"];

const ACTION_REVIEW_OPTIONS: Array<{ value: ActionReviewOutcome; label: string }> = [
  { value: "approved_for_prepare", label: "zatwierdzone do przygotowania" },
  { value: "needs_changes", label: "wymaga poprawek" },
  { value: "rejected", label: "odrzucone" },
  { value: "deferred", label: "odłożone" }
];

export function ActionHumanReviewControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const [outcome, setOutcome] = useState<ActionReviewOutcome>("approved_for_prepare");
  const [notes, setNotes] = useState(
    "Review operatora: zapisuję decyzję bez uruchamiania apply."
  );
  const reviewMutation = useMutation({
    mutationFn: () =>
      reviewAction(action.id, {
        outcome,
        reviewed_by: "operator_local_dashboard",
        notes: notes.trim(),
        checked_items: action.review_gate.operator_checklist.slice(0, 8),
        blockers: action.review_gate.apply_blockers.slice(0, 8)
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const lastOutcome = action.review_gate.last_review_outcome;
  const lastReviewLabel = lastOutcome
    ? ACTION_REVIEW_OPTIONS.find((option) => option.value === lastOutcome)?.label ?? lastOutcome
    : null;
  const canSave = notes.trim().length > 0 && !reviewMutation.isPending;

  return (
    <div className="mt-3 rounded-md border border-line bg-white p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Wynik review człowieka
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Zapisuje lokalny audit event. Nie wykonuje apply ani mutacji vendorów.
          </p>
        </div>
        <StatusBadge value={lastReviewLabel ?? "brak review"} />
      </div>
      {action.review_gate.last_review_summary ? (
        <p className="mt-2 rounded-md border border-line bg-slate-50 p-2 leading-5 text-slate-600">
          {action.review_gate.last_review_summary}
        </p>
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
          <span className="font-medium text-slate-600">Notatka review</span>
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
            {reviewMutation.isPending ? "Zapisuję" : "Zapisz review"}
          </button>
        </div>
      </div>
      {reviewMutation.data ? (
        <div className="mt-2 text-slate-600">
          Zapisano audit event: {reviewMutation.data.audit_event.event_type}
        </div>
      ) : null}
      {reviewMutation.error instanceof Error ? (
        <div className="mt-2 text-risk">Błąd review: {reviewMutation.error.message}</div>
      ) : null}
    </div>
  );
}

export function ActionReviewGatePanel({ action }: { action: ActionObject }) {
  const gate = action.review_gate;
  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Warunki przeglądu
          </div>
          <p className="mt-1 leading-5 text-slate-600">{gate.summary}</p>
        </div>
        <StatusBadge value={actionReviewGateStatusLabel(gate.status)} />
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <TraceLine
          label="Checklista"
          values={gate.operator_checklist.slice(0, 6).map(actionGateLabel)}
          empty="brak"
        />
        <TraceLine
          label="Blokady apply"
          values={gate.apply_blockers.slice(0, 8).map(actionGateLabel)}
          empty="brak"
        />
      </div>
      <div className="mt-2 text-slate-600">
        Potwierdzenie człowieka: {gate.confirmation_required ? "wymagane" : "niewymagane"}.
        Apply: {gate.apply_allowed ? "dopuszczony przez kontrakt" : "zablokowany"}.
      </div>
      {gate.last_confirmation_summary ? (
        <p className="mt-2 rounded-md border border-line bg-white p-2 text-slate-600">
          Ostatnie potwierdzenie: {gate.last_confirmation_summary}
        </p>
      ) : null}
      {gate.last_mutation_audit_summary ? (
        <div className="mt-2 rounded-md border border-risk/30 bg-white p-2 text-slate-600">
          <div className="font-semibold text-risk">Ostatni mutation audit</div>
          <p className="mt-1 leading-5">{gate.last_mutation_audit_summary}</p>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <div>Status: {actionMutationAuditStatusLabel(gate.last_mutation_audit_status)}</div>
            <div>Próba mutacji: {gate.last_mutation_attempted ? "tak" : "nie"}</div>
            <div>Adapter: {gate.last_mutation_adapter ?? "brak"}</div>
            <div>Audit event: {gate.last_mutation_audit_event_id ?? "brak"}</div>
          </div>
          <TraceLine
            label="Blockery mutacji"
            values={(gate.last_mutation_blockers ?? []).slice(0, 8).map(actionGateLabel)}
            empty="brak"
          />
        </div>
      ) : null}
    </div>
  );
}

function actionMutationAuditStatusLabel(value?: string | null) {
  const labels: Record<string, string> = {
    blocked: "zablokowany",
    applied: "wykonany",
    failed: "błąd"
  };
  return value ? labels[value] ?? value : "brak";
}

function actionReviewGateStatusLabel(value: string) {
  const labels: Record<string, string> = {
    pending_validation: "czeka na walidację",
    validated_prepare_only: "zwalidowane do review",
    ready_to_apply: "gotowe do potwierdzenia",
    blocked_apply: "apply zablokowany"
  };
  return labels[value] ?? value;
}

function actionGateLabel(value: string) {
  if (value.startsWith("blocked_claim:")) {
    return `claim zablokowany: ${adsBlockedClaimLabel(value.replace("blocked_claim:", ""))}`;
  }
  const labels: Record<string, string> = {
    action_mode_prepare_only: "tryb prepare-only",
    action_validation_required: "wymagana walidacja ActionObject",
    payload_apply_allowed_false: "payload nie pozwala na apply",
    destructive_actions_blocked: "destructive actions zablokowane",
    preview_acknowledgement_required: "wymagane potwierdzenie preview",
    dry_run_preview_required: "wymagany wcześniejszy dry-run preview",
    action_confirmation_required: "wymagane potwierdzenie preview",
    metric_facts_required: "wymagane metric facts",
    evidence_ids_required: "wymagane evidence IDs",
    impact_sanity_check_required: "wymagany impact sanity check",
    vendor_mutation_adapter_required: "brak adaptera mutacji vendorowej",
    validate_action_object: "walidacja ActionObject",
    human_review_before_apply: "review człowieka przed apply",
    human_confirm_before_apply: "potwierdzenie człowieka przed apply"
  };
  return labels[value] ?? adsMissingReadContractLabel(value);
}

export function ActionValidationControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const validationMutation = useMutation({
    mutationFn: () => validateAction(action.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const confirmMutation = useMutation({
    mutationFn: () =>
      confirmAction(action.id, {
        confirmed_by: "operator_local_dashboard",
        notes: "Operator potwierdza preview. Ten krok nie uruchamia apply.",
        preview_acknowledged: true
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  const validation = validationMutation.data;

  return (
    <div className="mt-3 rounded-md border border-line bg-slate-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
            Walidacja ActionObject
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            Walidacja sprawdza payload, connector, evidence IDs i tryb działania. Nie wykonuje
            apply.
          </p>
        </div>
        <button
          type="button"
          onClick={() => validationMutation.mutate()}
          disabled={validationMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {validationMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <CheckCircle2 aria-hidden="true" size={15} />
          )}
          {validationMutation.isPending ? "Waliduję" : "Waliduj"}
        </button>
      </div>
      <ActionValidationResultPanel
        validation={validation}
        error={validationMutation.error instanceof Error ? validationMutation.error.message : null}
      />
      <div className="mt-3 rounded-md border border-wait/30 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
          Jawne potwierdzenie preview
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Potwierdzenie wymaga wcześniejszego dry-run preview. Zapisuje lokalny audit event,
          ale nie wykonuje apply ani mutacji vendorów.
        </p>
        <button
          type="button"
          onClick={() => confirmMutation.mutate()}
          disabled={confirmMutation.isPending}
          className="mt-3 inline-flex min-h-9 items-center gap-2 rounded-md border border-wait bg-white px-3 py-2 text-xs font-medium text-wait hover:bg-wait/10 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {confirmMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <ShieldAlert aria-hidden="true" size={15} />
          )}
          {confirmMutation.isPending ? "Zapisuję potwierdzenie" : "Potwierdź preview"}
        </button>
        <ActionConfirmResultPanel
          result={confirmMutation.data}
          error={confirmMutation.error instanceof Error ? confirmMutation.error.message : null}
        />
      </div>
      <ActionImpactCheckControls action={action} />
    </div>
  );
}

function ActionValidationResultPanel({
  validation,
  error
}: {
  validation?: ActionValidationResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Błąd walidacji: {error}</div>;
  }
  if (!validation) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Wynik: <span className="font-semibold">{validation.valid ? "valid" : "invalid"}</span>
      </div>
      <TraceLine label="Błędy" values={validation.errors} empty="brak" />
      <TraceLine label="Ostrzeżenia" values={validation.warnings} empty="brak" />
    </div>
  );
}

function ActionConfirmResultPanel({
  result,
  error
}: {
  result?: ActionConfirmResult;
  error: string | null;
}) {
  if (error) {
    return (
      <div className="mt-3 text-xs leading-5 text-risk">
        Potwierdzenie zablokowane: {error}
      </div>
    );
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Potwierdzenie: <span className="font-semibold">{result.status}</span>
      </div>
      <TraceLine label="Blokady potwierdzenia" values={result.blockers.map(actionGateLabel)} empty="brak" />
      <div>Audit event: {result.audit_event.event_type}</div>
      <div>
        Apply nadal: {result.review_gate.apply_allowed ? "dopuszczony przez kontrakt" : "zablokowany"}.
      </div>
    </div>
  );
}

function ActionImpactCheckControls({ action }: { action: ActionObject }) {
  const queryClient = useQueryClient();
  const impactMutation = useMutation({
    mutationFn: () =>
      impactCheckAction(action.id, {
        checked_by: "operator_local_dashboard",
        notes: "Operator sprawdza sanity impact window przed jakimkolwiek apply.",
        pre_window_days: 7,
        post_window_days: 7
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });

  return (
    <div className="mt-3 rounded-md border border-line bg-white p-3 text-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="font-semibold uppercase tracking-normal text-slate-600">
            Impact sanity check
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Zapisuje pre/post window check na podstawie metryk ActionObjecta. Nie ocenia
            wzrostu i nie wykonuje apply.
          </p>
        </div>
        <button
          type="button"
          onClick={() => impactMutation.mutate()}
          disabled={impactMutation.isPending}
          className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-ink hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {impactMutation.isPending ? (
            <RefreshCw aria-hidden="true" className="animate-spin" size={15} />
          ) : (
            <ShieldAlert aria-hidden="true" size={15} />
          )}
          {impactMutation.isPending ? "Sprawdzam" : "Sprawdź impact"}
        </button>
      </div>
      {action.review_gate.last_impact_check_summary ? (
        <p className="mt-2 rounded-md border border-line bg-slate-50 p-2 leading-5 text-slate-600">
          Ostatni impact check: {action.review_gate.last_impact_check_summary}
        </p>
      ) : null}
      <ActionImpactCheckResultPanel
        result={impactMutation.data}
        error={impactMutation.error instanceof Error ? impactMutation.error.message : null}
      />
    </div>
  );
}

function ActionImpactCheckResultPanel({
  result,
  error
}: {
  result?: ActionImpactCheckResult;
  error: string | null;
}) {
  if (error) {
    return <div className="mt-3 text-xs leading-5 text-risk">Impact check zablokowany: {error}</div>;
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Impact check: <span className="font-semibold">{result.status}</span>
      </div>
      <div>
        Okna: {result.pre_window_days} dni przed / {result.post_window_days} dni po.
      </div>
      <div>Metric facts: {result.metric_fact_count}</div>
      <TraceLine label="Źródła" values={result.source_connectors} empty="brak" />
      <TraceLine label="Blokady impact" values={result.blockers.map(actionGateLabel)} empty="brak" />
      <div>Audit event: {result.audit_event.event_type}</div>
      <div>
        Apply nadal: {result.review_gate.apply_allowed ? "dopuszczony przez kontrakt" : "zablokowany"}.
      </div>
    </div>
  );
}

function SectionHeading({ title }: { title: string }) {
  return (
    <h2 className="mb-3 text-xs font-semibold uppercase tracking-normal text-slate-500">
      {title}
    </h2>
  );
}
