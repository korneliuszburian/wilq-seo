import { RefreshCw } from "lucide-react";

import type { ConnectorRefreshRun, ConnectorStatus } from "../../lib/api";
import {
  hasStaleSourceData,
  sourceAccessStatus
} from "./DecisionImpact";

export function SourceAccessCard({
  connector,
  onRefresh,
  refreshing,
  refreshError,
  refreshResult
}: {
  connector: ConnectorStatus;
  onRefresh: () => void;
  refreshing: boolean;
  refreshError: Error | null;
  refreshResult: ConnectorRefreshRun | null;
}) {
  const status = sourceAccessStatus(connector);
  const canRefresh = hasStaleSourceData(connector) && connector.refresh_state.refresh_allowed;
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">{connector.label}</h3>
          <p className="mt-2 text-xs leading-5 text-slate-600">
            {connector.product_scope_label || "Źródło danych sprawdzane przez WILQ."}
          </p>
        </div>
        <span className={`rounded px-2 py-1 text-xs font-semibold ${status.className}`}>
          {status.label}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">
        {status.description}
      </p>
      <div className="mt-3 rounded-md bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
        <span className="font-semibold text-ink">Stan odczytu: </span>
        {connector.refresh_state.state_label}. {connector.refresh_state.safe_next_step}
      </div>
      {canRefresh ? (
        <div className="mt-4 space-y-2">
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-md border border-wait/40 bg-white px-3 py-2 text-sm font-semibold text-wait disabled:cursor-wait disabled:opacity-70"
          >
            <RefreshCw
              size={15}
              aria-hidden="true"
              className={refreshing ? "animate-spin" : undefined}
            />
            {refreshing ? "Odświeżam dane" : "Odśwież dane"}
          </button>
          {refreshError ? (
            <p className="text-xs leading-5 text-risk">
              Nie udało się uruchomić lub sprawdzić odczytu źródła. Stan pozostaje niepotwierdzony;
              sprawdź dostęp albo spróbuj ponownie.
            </p>
          ) : refreshResult ? (
            <p className={`text-xs leading-5 ${refreshing ? "text-wait" : "text-success"}`}>
              {refreshing
                ? refreshResult.status_label || "Odczyt trwa; poczekaj na wynik."
                : refreshResult.status === "failed" || refreshResult.status === "blocked"
                  ? refreshResult.status_label || "Odczyt zablokowany; sprawdź dostęp."
                  : "Odczyt zakończony. WILQ odświeży decyzje po aktualizacji źródła."}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
