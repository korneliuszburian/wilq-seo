import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ContentNewPageDraftBindingSchema } from "@wilq/shared-schemas";
import type { z } from "zod";
import { CheckCircle2, RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";

import {
  type ActionConfirmResult,
  type ActionImpactCheckResult,
  type ActionValidationResult,
  applyAction,
  confirmAction,
  impactCheckAction,
  validateAction
} from "../../lib/api";
import { TraceLine } from "../../components/TraceLine";
import type { ActionObject, ActionPanelProps } from "./shared";

type ContentNewPageDraftBinding = z.infer<typeof ContentNewPageDraftBindingSchema>;

export function ActionValidationControls({ action }: ActionPanelProps) {
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
        notes: "Operator potwierdza podgląd. Ten krok nie zapisuje zmian.",
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
            Sprawdzenie w WILQ
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            WILQ sprawdza dane akcji, źródło, dowody i tryb działania. Ten krok nie zapisuje zmian.
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
          {validationMutation.isPending ? "Sprawdzam" : "Sprawdź w WILQ"}
        </button>
      </div>
      <ActionValidationResultPanel
        validation={validation}
        error={validationMutation.error instanceof Error ? validationMutation.error.message : null}
      />
      <div className="mt-3 rounded-md border border-wait/30 bg-white p-3">
        <div className="text-xs font-semibold uppercase tracking-normal text-slate-600">
          Jawne potwierdzenie podglądu
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-600">
          Potwierdzenie wymaga wcześniejszego podglądu zmian. Zapisuje lokalne zdarzenie audytu,
          ale nie zapisuje zmian w zewnętrznych systemach.
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
          {confirmMutation.isPending ? "Zapisuję potwierdzenie" : "Potwierdź podgląd"}
        </button>
        <ActionConfirmResultPanel
          result={confirmMutation.data}
          error={confirmMutation.error instanceof Error ? confirmMutation.error.message : null}
        />
      </div>
      <ActionImpactCheckControls action={action} />
      <ActionNewPageDraftApplyControl action={action} />
    </div>
  );
}

function newPageDraftBinding(action: ActionObject): ContentNewPageDraftBinding | null {
  if (action.payload.action_type !== "content_new_page_dev_draft_create") return null;
  const parsed = ContentNewPageDraftBindingSchema.safeParse(action.payload.new_page_draft_binding);
  return parsed.success ? parsed.data : null;
}

export function ActionNewPageDraftApplyControl({ action }: ActionPanelProps) {
  const binding = newPageDraftBinding(action);
  const queryClient = useQueryClient();
  const [confirmedBy, setConfirmedBy] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const applyMutation = useMutation({
    mutationFn: () =>
      applyAction(action.id, {
        confirm: true,
        confirmed_by: confirmedBy,
        new_page_draft: binding!
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["actions", action.id] });
      void queryClient.invalidateQueries({ queryKey: ["marketing-brief"] });
    }
  });
  if (!binding) return null;
  const canApply = action.review_gate.apply_allowed && acknowledged && confirmedBy.trim().length >= 2;
  return (
    <section
      className="mt-3 rounded-md border border-indigo-200 bg-indigo-50/60 p-3 text-xs"
      data-testid="new-page-draft-apply"
    >
      <div className="font-semibold uppercase tracking-normal text-indigo-800">
        Utwórz jeden szkic na dev
      </div>
      <p className="mt-1 leading-5 text-slate-700">
        Ta czynność dotyczy exact rewizji {binding.revision_digest.slice(0, 12)}… i tworzy
        wyłącznie nowy szkic na dev. Nie publikuje, nie aktualizuje ani nie usuwa treści.
      </p>
      <label className="mt-3 block font-medium text-slate-700">
        Potwierdza
        <input
          value={confirmedBy}
          onChange={(event) => setConfirmedBy(event.target.value)}
          placeholder="Imię i nazwisko"
          className="mt-1 block w-full rounded-md border border-line bg-white px-2 py-2 text-xs text-ink"
        />
      </label>
      <label className="mt-3 flex items-start gap-2 leading-5 text-slate-700">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(event) => setAcknowledged(event.target.checked)}
          className="mt-0.5"
        />
        Potwierdzam podgląd, review, evidence oraz fakt, że chcę utworzyć jeden szkic na dev.
      </label>
      {!action.review_gate.apply_allowed ? (
        <p className="mt-2 text-risk">
          Zapis pozostaje zablokowany przez bieżące bramki ActionObjectu.
        </p>
      ) : null}
      <button
        type="button"
        onClick={() => applyMutation.mutate()}
        disabled={!canApply || applyMutation.isPending}
        className="mt-3 inline-flex min-h-9 items-center rounded-md bg-action px-3 py-2 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
      >
        {applyMutation.isPending ? "Tworzę szkic…" : "Utwórz szkic na dev"}
      </button>
      {applyMutation.data ? (
        <p className="mt-2 leading-5 text-action">
          {applyMutation.data.applied
            ? "Szkic na dev został utworzony. WILQ nie opublikował strony."
            : applyMutation.data.errors.join(" ")}
        </p>
      ) : null}
      {applyMutation.isError ? (
        <p className="mt-2 leading-5 text-risk">
          Szkic nie został utworzony. Odśwież ActionObject i sprawdź jego exact bramki.
        </p>
      ) : null}
    </section>
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
    return <div className="mt-3 text-xs leading-5 text-risk">Błąd sprawdzenia: {error}</div>;
  }
  if (!validation) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Wynik: <span className="font-semibold">{validation.status_label}</span>
      </div>
      <TraceLine
        label="Błędy"
        values={validation.errors}
        empty="WILQ nie zgłosił błędów sprawdzenia."
      />
      <TraceLine
        label="Ostrzeżenia"
        values={validation.warnings}
        empty="WILQ nie zgłosił ostrzeżeń sprawdzenia."
      />
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
        Potwierdzenie: <span className="font-semibold">{result.status_label}</span>
      </div>
      <TraceLine
        label="Blokady potwierdzenia"
        values={result.blocker_labels}
        empty="WILQ nie zgłosił blokad potwierdzenia."
      />
      <div>Ślad bezpieczeństwa: {result.audit_event.event_type_label}</div>
      <div>
        Zapis zmian nadal: {result.review_gate.apply_allowed ? "dopuszczony" : "zablokowany"}.
      </div>
    </div>
  );
}

function ActionImpactCheckControls({ action }: ActionPanelProps) {
  const queryClient = useQueryClient();
  const impactMutation = useMutation({
    mutationFn: () =>
      impactCheckAction(action.id, {
        checked_by: "operator_local_dashboard",
        notes: "Operator sprawdza porównanie efektu przed jakimkolwiek zapisem zmian.",
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
            Sprawdzenie efektu
          </div>
          <p className="mt-1 leading-5 text-slate-600">
            Zapisuje porównanie wyników sprzed zmiany i po zmianie na podstawie
            metryk akcji. Nie ocenia wzrostu i nie zapisuje zmian.
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
          {impactMutation.isPending ? "Sprawdzam" : "Sprawdź efekt"}
        </button>
      </div>
      {action.review_gate.last_impact_check_summary ? (
        <p className="mt-2 rounded-md border border-line bg-slate-50 p-2 leading-5 text-slate-600">
          Ostatnie sprawdzenie efektu: zapisane. Szczegóły metryk i blokad są dostępne w panelu wyniku.
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
    return (
      <div className="mt-3 text-xs leading-5 text-risk">
        Sprawdzenie efektu zablokowane: {error}
      </div>
    );
  }
  if (!result) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs text-slate-700">
      <div>
        Sprawdzenie efektu: <span className="font-semibold">{result.status_label}</span>
      </div>
      <div>
        Porównanie: {result.pre_window_days} dni przed zmianą / {result.post_window_days} dni po zmianie.
      </div>
      <div>Metryki z dowodami: {result.metric_fact_count}</div>
      <TraceLine
        label="Źródła"
        values={result.source_connector_labels}
        empty="WILQ nie podał źródeł danych; nie oceniaj efektu bez źródła."
      />
      <div>
        Dowody:{" "}
        {result.evidence_summary_label ||
          "WILQ nie podał dowodów źródłowych; sprawdzenie efektu nie uzasadnia wniosku."}
      </div>
      <TraceLine
        label="Blokady sprawdzenia efektu"
        values={result.blocker_labels}
        empty="WILQ nie zgłosił blokad sprawdzenia efektu."
      />
      <div>Ślad bezpieczeństwa: {result.audit_event.event_type_label}</div>
      <div>
        Zapis zmian nadal: {result.review_gate.apply_allowed ? "dopuszczony" : "zablokowany"}.
      </div>
    </div>
  );
}
