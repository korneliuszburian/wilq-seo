import { useEffect, useRef, useState } from "react";

import {
  getConnectorRefreshRun,
  refreshConnector,
  type ConnectorRefreshRun
} from "../lib/api";

type Props = {
  connectorIds: string[];
  connectorLabels: Record<string, string>;
  onCompleted: () => void;
};

/**
 * Keeps a source blocker actionable without turning the Content entry into a
 * connector administration screen. Only connector IDs that the API freshness
 * assessment marked stale or missing can be requested here.
 */
export function ContentRequiredSourceRefresh({
  connectorIds,
  connectorLabels,
  onCompleted
}: Props) {
  const pollTimeoutRef = useRef<number | null>(null);
  const [activeConnectorId, setActiveConnectorId] = useState<string | null>(null);
  const [run, setRun] = useState<ConnectorRefreshRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const clearPoll = () => {
    if (pollTimeoutRef.current !== null) {
      window.clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  useEffect(() => () => clearPoll(), []);

  const finish = (completedRun: ConnectorRefreshRun) => {
    setRun(completedRun);
    clearPoll();
    setActiveConnectorId(null);
    if (completedRun.status === "completed") onCompleted();
  };

  const poll = async (runId: string) => {
    try {
      const refreshedRun = await getConnectorRefreshRun(runId);
      setRun(refreshedRun);
      if (isRunning(refreshedRun.status)) {
        pollTimeoutRef.current = window.setTimeout(() => void poll(runId), 1_000);
        return;
      }
      finish(refreshedRun);
    } catch {
      clearPoll();
      setActiveConnectorId(null);
      setError("Nie udało się sprawdzić statusu odczytu. Możesz ponowić sprawdzenie źródła.");
    }
  };

  const start = async (connectorId: string) => {
    if (activeConnectorId) return;
    clearPoll();
    setActiveConnectorId(connectorId);
    setRun(null);
    setError(null);
    try {
      const createdRun = await refreshConnector(connectorId);
      setRun(createdRun);
      if (isRunning(createdRun.status)) {
        void poll(createdRun.id);
        return;
      }
      finish(createdRun);
    } catch {
      setActiveConnectorId(null);
      setError("Nie udało się uruchomić odczytu. Stan źródeł nie został zmieniony.");
    }
  };

  if (!connectorIds.length) return null;
  return (
    <section className="mt-4 rounded-xl border border-action/25 bg-white p-4" data-testid="content-required-source-refresh">
      <p className="font-semibold text-ink">Odczytaj wymagane źródła</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">
        Ten krok pobiera wyłącznie aktualne dane do WILQ. Nie zmienia treści ani nie publikuje w WordPressie.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {connectorIds.map((connectorId) => {
          const isActive = activeConnectorId === connectorId;
          const label = connectorLabels[connectorId] ?? connectorId;
          return <button
            key={connectorId}
            type="button"
            className="rounded-md border border-action/30 bg-white px-3 py-2 text-sm font-semibold text-action hover:bg-action/5 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={Boolean(activeConnectorId)}
            onClick={() => void start(connectorId)}
          >
            {isActive ? `Odczytuję ${label}…` : `Odczytaj ${label}`}
          </button>;
        })}
      </div>
      {run ? <div className="mt-3 rounded-lg bg-slate-50 p-3 text-sm leading-6 text-slate-700" role="status">
        <p className="font-semibold text-ink">{run.status_label}</p>
        <p className="mt-1">{run.errors[0] ?? run.summary}</p>
      </div> : null}
      {error ? <p className="mt-3 text-sm font-semibold text-wait" role="status">{error}</p> : null}
    </section>
  );
}

function isRunning(status: ConnectorRefreshRun["status"]) {
  return status === "queued" || status === "running";
}
