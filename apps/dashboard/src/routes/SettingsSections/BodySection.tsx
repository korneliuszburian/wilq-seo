import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { BlockerNotice } from "../../components/OperatorPrimitives";
import {
  getConnectorRefreshRun,
  refreshConnector,
  type ConnectorRefreshRun,
  type ConnectorStatus
} from "../../lib/api";
import { ConnectorGrid } from "../RegistryPanels";
import {
  buildSourceImpactRows,
  formatConnectorList,
  hasMissingSourceAccess,
  hasStaleSourceData,
  pluralize
} from "./DecisionImpact";
import { SourceAccessCard } from "./SourceAccessCard";
import { DetailToggle, SourceStatTile } from "./StatusBar";

export function SettingsSurfaceSections({ connectors }: { connectors: ConnectorStatus[] }) {
  const [showConnectorDetails, setShowConnectorDetails] = useState(false);
  const [refreshRunsByConnector, setRefreshRunsByConnector] = useState<
    Record<string, ConnectorRefreshRun>
  >({});
  const [refreshRunErrors, setRefreshRunErrors] = useState<Record<string, Error>>({});
  const automaticRefreshes = useRef(new Set<string>());
  const completedRefreshes = useRef(new Set<string>());
  const activeRefreshPolls = useRef(new Set<string>());
  const refreshPollTimeouts = useRef(new Map<string, number>());
  const queryClient = useQueryClient();
  const pollRefreshRun = useCallback(
    (connectorId: string, runId: string) => {
      if (activeRefreshPolls.current.has(runId)) return;
      activeRefreshPolls.current.add(runId);

      const scheduleNextPoll = () => {
        const timeoutId = window.setTimeout(() => {
          refreshPollTimeouts.current.delete(runId);
          void poll();
        }, 500);
        refreshPollTimeouts.current.set(runId, timeoutId);
      };
      const poll = async () => {
        let run: ConnectorRefreshRun;
        try {
          run = await getConnectorRefreshRun(runId);
        } catch {
          setRefreshRunErrors((current) => ({
            ...current,
            [connectorId]: new Error(
              "Nie udało się sprawdzić statusu odświeżenia; stan źródła pozostaje niepotwierdzony."
            )
          }));
          activeRefreshPolls.current.delete(runId);
          refreshPollTimeouts.current.delete(runId);
          return;
        }

        setRefreshRunErrors((current) => {
          if (!current[connectorId]) return current;
          const remaining = { ...current };
          delete remaining[connectorId];
          return remaining;
        });
        setRefreshRunsByConnector((current) => ({ ...current, [connectorId]: run }));
        if (!isRefreshRunInProgress(run.status)) {
          activeRefreshPolls.current.delete(runId);
          refreshPollTimeouts.current.delete(runId);
          return;
        }

        scheduleNextPoll();
      };

      scheduleNextPoll();
    },
    []
  );
  const refreshMutation = useMutation({
    mutationFn: refreshConnector,
    onSuccess: (run) => {
      setRefreshRunsByConnector((current) => ({ ...current, [run.connector_id]: run }));
      setRefreshRunErrors((current) => {
        if (!current[run.connector_id]) return current;
        const remaining = { ...current };
        delete remaining[run.connector_id];
        return remaining;
      });
      if (isRefreshRunInProgress(run.status)) {
        pollRefreshRun(run.connector_id, run.id);
      }
    }
  });

  useEffect(
    () => () => {
      refreshPollTimeouts.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
      refreshPollTimeouts.current.clear();
      activeRefreshPolls.current.clear();
    },
    []
  );

  useEffect(() => {
    Object.values(refreshRunsByConnector).forEach((run) => {
      if (
        isRefreshRunInProgress(run.status)
        || completedRefreshes.current.has(run.id)
      ) {
        return;
      }
      completedRefreshes.current.add(run.id);
      const affectedDecisions = connectors.find((connector) => connector.id === run.connector_id)
        ?.refresh_state.affected_decisions ?? [];
      invalidateSourceDependentQueries(queryClient, affectedDecisions);
    });
  }, [connectors, queryClient, refreshRunsByConnector]);

  useEffect(() => {
    connectors.forEach((connector) => {
      if (
        !connector.refresh_state.automatic_refresh.eligible
        || automaticRefreshes.current.has(connector.id)
      ) {
        return;
      }
      automaticRefreshes.current.add(connector.id);
      refreshMutation.mutate(connector.id);
    });
  }, [connectors, refreshMutation]);
  const missing = connectors.filter((connector) => hasMissingSourceAccess(connector));
  const freshDailySources = connectors.filter(
    (connector) =>
      connector.active_for_daily_work
      && connector.configured
      && !hasMissingSourceAccess(connector)
      && !hasStaleSourceData(connector)
  );
  const staleDailySources = connectors.filter(hasStaleSourceData);
  const outsideDailyScope = connectors.filter((connector) => !connector.active_for_daily_work);
  const sourceImpactRows = buildSourceImpactRows(missing, staleDailySources, outsideDailyScope);

  if (connectors.length === 0) {
    return (
      <section>
        <BlockerNotice message="WILQ nie ma statusu źródeł danych; odśwież integracje przed oceną gotowości." />
      </section>
    );
  }

  return (
    <>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SourceStatTile value={connectors.length} label="źródeł" tone="default" />
        <SourceStatTile value={freshDailySources.length} label="gotowe dziennie" tone="success" />
        <SourceStatTile value={missing.length} label="brak dostępu" tone="risk" />
        <SourceStatTile value={staleDailySources.length} label="wymagają odświeżenia" tone="wait" />
      </section>

      <section className="rounded-md border border-wait/40 bg-wait/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-ink">Co blokuje pracę</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-700">
              {missing.length > 0
                ? `Brakuje dostępu do ${formatConnectorList(missing)}. WILQ może dalej używać skonfigurowanych źródeł, ale nie powinien opierać decyzji na danych z brakujących kanałów.`
                : "Braki dostępu nie blokują teraz głównej pracy."}
              {staleDailySources.length > 0
                ? ` ${staleDailySources.length} ${pluralize(
                    staleDailySources.length,
                    "źródło wymaga",
                    "źródła wymagają",
                    "źródeł wymaga"
                  )} odświeżenia przed oceną wyników.`
                : " Dane są gotowe do dziennej pracy po sprawdzeniu zakresu decyzji."}
            </p>
          </div>
          <a
            href="#source-impact"
            className="rounded-md border border-wait/40 bg-white px-4 py-2 text-sm font-semibold text-wait"
          >
            Zobacz szczegóły
          </a>
        </div>
      </section>

      <section className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Dostęp do źródeł</h2>
        </div>
        <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-4">
          {connectors.map((connector) => {
            const trackedRefreshRun = refreshRunsByConnector[connector.id];
            const refreshRunError = refreshRunErrors[connector.id] ?? null;
            const mutationRefreshRun =
              refreshMutation.data?.connector_id === connector.id ? refreshMutation.data : null;
            const refreshResult = trackedRefreshRun ?? mutationRefreshRun;
            return (
              <SourceAccessCard
                key={connector.id}
                connector={connector}
                onRefresh={() => refreshMutation.mutate(connector.id)}
                refreshing={
                  (refreshMutation.isPending && refreshMutation.variables === connector.id)
                  || (!refreshRunError && isRefreshRunInProgress(refreshResult?.status))
                }
                refreshError={
                  refreshMutation.error && refreshMutation.variables === connector.id
                    ? refreshMutation.error
                    : refreshRunError
                }
                refreshResult={refreshResult}
              />
            );
          })}
        </div>
      </section>

      <section id="source-impact" className="rounded-md border border-line bg-white">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-base font-semibold text-ink">Wpływ braków na decyzje</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Źródło</th>
                <th className="px-4 py-3 font-semibold">Co jest zablokowane</th>
                <th className="px-4 py-3 font-semibold">Wpływ na decyzje</th>
                <th className="px-4 py-3 font-semibold">Następny krok</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {sourceImpactRows.map((row) => (
                <tr key={row.id}>
                  <td className="px-4 py-3 font-medium text-ink">{row.source}</td>
                  <td className="px-4 py-3 text-slate-700">{row.blocked}</td>
                  <td className="px-4 py-3 text-slate-700">
                    <span className={`mr-2 inline-block h-2 w-2 rounded-full ${row.dotClass}`} />
                    {row.impact}
                  </td>
                  <td className="px-4 py-3 font-medium text-action">{row.nextStep}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-md border border-line bg-white p-4">
        <h2 className="text-base font-semibold text-ink">Eksport i pakiety</h2>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-md border border-action/30 bg-action/5 p-3">
          <p className="max-w-4xl text-sm leading-6 text-slate-700">
            Eksporty do Google Sheets są ograniczone do pakietów i zakresów bezpiecznych.
            Pełny eksport raportów i rejestru WILQ będzie dostępny po wdrożeniu zasad
            bezpiecznego eksportu.
          </p>
          <span className="rounded-md border border-wait/30 bg-white px-4 py-2 text-sm font-semibold text-wait">
            Eksport zablokowany
          </span>
        </div>
      </section>

      <section>
        <DetailToggle
          expanded={showConnectorDetails}
          label="Pokaż szczegóły techniczne źródeł"
          onClick={() => setShowConnectorDetails((value) => !value)}
        />
        {showConnectorDetails ? (
          <div className="mt-3">
            <ConnectorGrid connectors={connectors} />
          </div>
        ) : null}
      </section>
    </>
  );
}

const sourceDecisionQueryKeys: Record<string, string> = {
  ads_diagnostics: "ads-diagnostics",
  command_center: "command-center",
  content_diagnostics: "content-diagnostics",
  ga4_diagnostics: "ga4-diagnostics",
  merchant_diagnostics: "merchant-diagnostics"
};

function invalidateSourceDependentQueries(queryClient: QueryClient, affectedDecisions: string[]) {
  void queryClient.invalidateQueries({ queryKey: ["connectors"] });
  affectedDecisions.forEach((decision) => {
    const queryKey = sourceDecisionQueryKeys[decision];
    if (queryKey) {
      void queryClient.invalidateQueries({ queryKey: [queryKey] });
    }
  });
}

function isRefreshRunInProgress(status: ConnectorRefreshRun["status"] | null | undefined) {
  return status === "queued" || status === "running";
}
