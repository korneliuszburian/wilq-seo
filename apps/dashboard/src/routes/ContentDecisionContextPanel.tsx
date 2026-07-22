import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import {
  getConnectorRefreshRun,
  refreshConnector,
  type ConnectorRefreshRun,
  type ContentDecisionContext
} from "../lib/api";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";
import { contentDecisionContextQueryKey } from "./contentWorkflowQueries";

export function ContentDecisionContextPanel({
  context,
  onOpenTextWorkspace
}: {
  context: ContentDecisionContext;
  onOpenTextWorkspace?: (workItemId: string) => void;
}) {
  const action = context.next_safe_action;
  const disclosures = technicalDisclosures(context);
  return (
    <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-decision-context">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Wybrana strona</p>
        <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <h1 className="text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
              {context.source_public.title ?? "Wybrana strona"}
            </h1>
            {context.source_public.url ? (
              <a
                className="mt-2 block break-all text-sm text-action underline underline-offset-2"
                href={context.source_public.url}
                rel="noreferrer"
                target="_blank"
              >
                {context.source_public.url}
              </a>
            ) : null}
            <p className="mt-2 text-sm font-medium text-slate-700">
              Usługa: {context.service.label ?? "niepotwierdzona"}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-700">Wynik pracy: pełna rewizja HTML do review.</p>
          </div>
          <span className="rounded-full border border-wait/30 bg-wait/10 px-3 py-1.5 text-xs font-semibold text-wait">
            {context.work_kind === "refresh_existing" ? "Odświeżenie istniejącej strony" : "Rodzaj pracy do ustalenia"}
          </span>
        </div>
      </section>

      <NextSafeAction action={action} workItemId={context.work_item_id} onOpenTextWorkspace={onOpenTextWorkspace} />

      <section className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="rounded-2xl border border-line bg-white p-4 shadow-sm lg:p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Dlaczego teraz?</p>
          {context.applicable_signals.length ? (
            <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {context.applicable_signals.map((signal) => (
                <div key={`${signal.source_connector}:${signal.label}`} className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{signal.label}</p>
                  <p className="mt-1 truncate text-lg font-semibold text-ink">{formatSignalValue(signal.value)}</p>
                </div>
              ))}
            </div>
          ) : <p className="mt-3 text-sm leading-6 text-slate-700">{context.evidence_readiness.reason}</p>}
          <p className="mt-3 text-xs leading-5 text-slate-600">{signalFreshnessNote(context)}</p>
        </div>
        <div className="rounded-2xl border border-line bg-slate-50 p-4 shadow-sm lg:p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Rekomendacja WILQ</p>
          <p className="mt-2 text-base font-semibold text-ink">{context.decision_disposition.label}</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">Ostateczną decyzję podejmuje marketer.</p>
        </div>
      </section>

      <section className="mt-4 rounded-2xl border border-line bg-white p-4 shadow-sm lg:p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Stan pracy</p>
        <ol className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-slate-600" aria-label="Stan pipeline’u">
          <li className="text-action">Kontekst</li><li aria-hidden="true">→</li><li>Szkic</li><li aria-hidden="true">→</li><li>Review</li><li aria-hidden="true">→</li><li>Odbiór opcjonalny</li>
        </ol>
      </section>

      <details className="mt-4 rounded-xl border border-line bg-white p-4 text-sm text-slate-700">
          <summary className="cursor-pointer font-semibold text-ink">Szczegóły, źródła i ograniczenia</summary>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <ContextCard label="Publiczne źródło" value={context.source_public.label} detail={context.source_public.reason} compact />
            <ContextCard label="Target dev" value={context.authoring_target.label} detail={context.authoring_target.reason} compact />
            <ContextCard label="Relacja source → target" value={context.source_target_relation.label} detail={context.source_target_relation.reason} compact />
            <ContextCard label="Rozpoznanie obiektu" value={context.object_readiness.label} detail={context.object_readiness.reason} compact />
            <ContextCard label="Dowody" value={context.evidence_readiness.label} detail={context.evidence_readiness.reason} compact />
            <ContextCard label="Odbiór opcjonalny" value={context.delivery_capability.label} detail={context.delivery_capability.reason} compact />
            <ContextCard label="Pomiar" value={context.measurement_target.label} detail={context.measurement_target.reason} compact />
          </div>
          {disclosures.length ? <ul className="mt-3 space-y-2 leading-6">
            {disclosures.map((disclosure) => (
              <li key={disclosure.id}>
                <span className="font-semibold">{disclosure.label}: </span>
                {disclosure.summary}
              </li>
            ))}
          </ul> : null}
        </details>
    </main>
  );
}

function NextSafeAction({
  action,
  workItemId,
  onOpenTextWorkspace
}: {
  action: ContentDecisionContext["next_safe_action"];
  workItemId: string;
  onOpenTextWorkspace?: (workItemId: string) => void;
}) {
  const queryClient = useQueryClient();
  const startedRef = useRef(false);
  const pollTimeoutRef = useRef<number | null>(null);
  const [isStarted, setIsStarted] = useState(false);
  const [run, setRun] = useState<ConnectorRefreshRun | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [contextRefetchStatus, setContextRefetchStatus] = useState<"idle" | "loading" | "error">("idle");

  const clearPoll = () => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  useEffect(
    () => () => {
      if (pollTimeoutRef.current !== null) window.clearTimeout(pollTimeoutRef.current);
    },
    []
  );

  const refetchContext = async () => {
    setContextRefetchStatus("loading");
    try {
      await queryClient.refetchQueries(
        {
          queryKey: contentDecisionContextQueryKey(workItemId),
          exact: true
        },
        { throwOnError: true }
      );
      startedRef.current = false;
      setIsStarted(false);
      setContextRefetchStatus("idle");
    } catch {
      setContextRefetchStatus("error");
    }
  };

  const finishRun = async (finishedRun: ConnectorRefreshRun) => {
    setRun(finishedRun);
    clearPoll();
    if (finishedRun.status === "completed") {
      await refetchContext();
      return;
    }
    startedRef.current = false;
    setIsStarted(false);
  };

  const pollRun = async (runId: string) => {
    try {
      const refreshedRun = await getConnectorRefreshRun(runId);
      setRun(refreshedRun);
      if (isRunInProgress(refreshedRun.status)) {
        pollTimeoutRef.current = window.setTimeout(() => void pollRun(runId), 500);
        return;
      }
      await finishRun(refreshedRun);
    } catch {
      clearPoll();
      setRunError("Nie udało się sprawdzić statusu odświeżenia; ponów sprawdzenie tego samego runu.");
    }
  };

  const refreshMutation = useMutation({
    mutationFn: refreshConnector,
    onSuccess: (createdRun) => {
      setRun(createdRun);
      if (isRunInProgress(createdRun.status)) {
        void pollRun(createdRun.id);
        return;
      }
      void finishRun(createdRun);
    },
    onError: () => {
      startedRef.current = false;
      setIsStarted(false);
      setRunError("Nie udało się uruchomić odświeżenia źródła; kontekst strony nie został zmieniony.");
    }
  });

  const connectorId = action.kind === "refresh_connector" ? action.connector_id : null;
  const connectorName = connectorDisplayName(action, connectorId);
  const canOpenWorkspace = action.kind === "open_workspace" && onOpenTextWorkspace !== undefined;
  const canRetryPoll = Boolean(runError && run && isRunInProgress(run.status));
  const canRetryContext = Boolean(contextRefetchStatus === "error" && run?.status === "completed");
  const canStart = Boolean(connectorId) && !isStarted && !refreshMutation.isPending;
  const buttonEnabled = canStart || canRetryPoll || canRetryContext || canOpenWorkspace;
  const startRefresh = () => {
    if (canOpenWorkspace) {
      onOpenTextWorkspace(workItemId);
      return;
    }
    if (canRetryContext) {
      void refetchContext();
      return;
    }
    if (canRetryPoll && run) {
      setRunError(null);
      void pollRun(run.id);
      return;
    }
    if (!connectorId || startedRef.current || refreshMutation.isPending) return;
    startedRef.current = true;
    setIsStarted(true);
    clearPoll();
    setRun(null);
    setRunError(null);
    setContextRefetchStatus("idle");
    refreshMutation.mutate(connectorId);
  };

  return (
    <section className="mt-4 rounded-2xl border border-wait/30 bg-wait/10 p-4 shadow-sm lg:p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Najważniejsze teraz</p>
      <h2 className="mt-1 text-lg font-semibold text-ink">{action.label}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{action.reason}</p>
      {connectorId || canOpenWorkspace ? (
        <button
          type="button"
          className="mt-4 inline-flex rounded-md border border-action/30 bg-white px-3 py-2 text-sm font-semibold text-action hover:bg-action/5"
          disabled={!buttonEnabled}
          onClick={startRefresh}
        >
          {canOpenWorkspace
            ? "Otwórz warsztat strony"
            : canRetryContext
            ? "Sprawdź ponownie kontekst strony"
            : canRetryPoll
            ? `Sprawdź ponownie status ${connectorName}`
            : isRunInProgress(run?.status) || refreshMutation.isPending
            ? `Odświeżam ${connectorName}…`
            : action.label}
        </button>
      ) : null}
      {run ? <RefreshRunStatus run={run} isRefetchingContext={contextRefetchStatus === "loading"} /> : null}
      {runError ? <p className="mt-3 text-sm font-semibold text-wait" role="status">{runError}</p> : null}
      {contextRefetchStatus === "error" ? (
        <p className="mt-3 text-sm font-semibold text-wait" role="status">
          Nie udało się ponownie pobrać kontekstu strony; odświeżenie źródła nie zostaje uznane za gotowość dowodów.
        </p>
      ) : null}
    </section>
  );
}

function RefreshRunStatus({ run, isRefetchingContext }: { run: ConnectorRefreshRun; isRefetchingContext: boolean }) {
  const detail = run.errors[0] ?? run.summary;
  return (
    <div className="mt-3 rounded-xl border border-line bg-white/70 p-3 text-sm text-slate-700" role="status">
      <p className="font-semibold text-ink">{run.status_label}</p>
      <p className="mt-1 leading-6">{detail}</p>
      {run.status === "completed" && isRefetchingContext ? <p className="mt-2 text-xs text-slate-600">Sprawdzam ponownie kontekst strony.</p> : null}
    </div>
  );
}

function isRunInProgress(status: ConnectorRefreshRun["status"] | undefined): boolean {
  return status === "queued" || status === "running";
}

function ContextCard({
  label,
  value,
  detail,
  compact = false
}: {
  label: string;
  value: string;
  detail?: string;
  compact?: boolean;
}) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-slate-50 ${compact ? "p-3" : "p-4"}`}>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 font-semibold text-ink ${compact ? "text-sm" : "text-base"}`}>{value}</p>
      {detail ? <p className="mt-2 text-xs leading-5 text-slate-600">{detail}</p> : null}
    </div>
  );
}

function technicalDisclosures(context: ContentDecisionContext) {
  return [
    ...context.secondary_disclosures,
    ...technicalDisclosure("source-api-reason", "Szczegóły rozpoznania źródła", context.source_public.technical_reason),
    ...technicalDisclosure("target-api-reason", "Szczegóły targetu dev", context.authoring_target.technical_reason),
    ...technicalDisclosure("relation-api-reason", "Szczegóły relacji", context.source_target_relation.technical_reason),
    ...technicalDisclosure("object-api-reason", "Szczegóły rozpoznania obiektu", context.object_readiness.technical_reason),
    ...technicalDisclosure("direction-api-reason", "Szczegóły kierunku pracy", context.decision_disposition.technical_reason),
    ...technicalDisclosure("evidence-api-reason", "Szczegóły dowodów", context.evidence_readiness.technical_reason),
    ...technicalDisclosure("delivery-api-reason", "Szczegóły przekazania", context.delivery_capability.technical_reason),
    ...technicalDisclosure("measurement-api-reason", "Szczegóły pomiaru", context.measurement_target.technical_reason)
  ];
}

function technicalDisclosure(id: string, label: string, summary: string | null | undefined) {
  return summary ? [{ id, label, summary }] : [];
}

function connectorDisplayName(
  action: ContentDecisionContext["next_safe_action"],
  connectorId: string | null | undefined
): string {
  const label = action.label.replace(/^Odśwież\s+/u, "").trim();
  return label || connectorId || "źródła";
}

function formatSignalValue(value: string | number): string {
  return typeof value === "number" ? value.toLocaleString("pl-PL") : value;
}

function signalFreshnessNote(context: ContentDecisionContext): string {
  const states = new Set(context.applicable_signals.map((signal) => signal.freshness_state));
  if (states.has("stale")) return "Dane wymagają odświeżenia; nie pokazujemy trendu bez porównywalnych okresów.";
  if (states.has("unknown")) return "Świeżość części danych jest nieznana; nie pokazujemy trendu bez porównywalnych okresów.";
  return "Dane są aktualne; nie pokazujemy trendu bez porównywalnych okresów.";
}
