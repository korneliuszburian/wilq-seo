import { useMutation, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, RefreshCw, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { BlockerNotice } from "../components/OperatorPrimitives";
import {
  getConnectorRefreshRun,
  refreshConnector,
  type ConnectorRefreshRun,
  type ConnectorStatus
} from "../lib/api";
import { ConnectorGrid } from "./RegistryPanels";

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

export function SourceStatTile({
  value,
  label,
  tone
}: {
  value: number;
  label: string;
  tone: "default" | "success" | "risk" | "wait";
}) {
  const toneClass =
    tone === "success"
      ? "bg-success/10 text-success"
      : tone === "risk"
        ? "bg-risk/10 text-risk"
        : tone === "wait"
          ? "bg-wait/10 text-wait"
          : "bg-action/10 text-action";
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center gap-4">
        <div className={`flex h-11 w-11 items-center justify-center rounded-full ${toneClass}`}>
          <ShieldCheck size={20} aria-hidden="true" />
        </div>
        <div>
          <div className="text-2xl font-semibold text-ink">{value}</div>
          <div className="text-sm text-slate-700">{label}</div>
        </div>
      </div>
    </article>
  );
}

function SourceAccessCard({
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

function sourceAccessStatus(connector: ConnectorStatus) {
  if (hasMissingSourceAccess(connector)) {
    return {
      label: "Brak dostępu",
      className: "bg-risk/10 text-risk",
      description: "Dostęp wymaga uzupełnienia przed decyzjami z tego kanału."
    };
  }
  if (!connector.active_for_daily_work) {
    return {
      label: "Poza zakresem",
      className: "bg-wait/10 text-wait",
      description: "Dane nie są liczone do głównego dziennego zakresu pracy."
    };
  }
  if (hasStaleSourceData(connector)) {
    return {
      label: "Do odświeżenia",
      className: "bg-wait/10 text-wait",
      description: "Dane są dostępne, ale nie powinny domykać decyzji bez świeżego odczytu."
    };
  }
  if (connector.configured) {
    return {
      label: "Aktywny",
      className: "bg-success/10 text-success",
      description: "Dane dostępne i aktualizowane przez WILQ."
    };
  }
  return {
    label: connector.status_label || "Do sprawdzenia",
    className: "bg-wait/10 text-wait",
    description: "Status wymaga sprawdzenia przed użyciem w decyzjach."
  };
}

function hasMissingSourceAccess(connector: ConnectorStatus) {
  return connector.missing_credentials.length > 0 || connector.status === "missing_credentials";
}

function hasStaleSourceData(connector: ConnectorStatus) {
  return (
    connector.active_for_daily_work
    && connector.configured
    && !hasMissingSourceAccess(connector)
    && connector.freshness.state === "stale"
  );
}

type SourceImpactRow = {
  id: string;
  source: string;
  blocked: string;
  impact: string;
  nextStep: string;
  dotClass: string;
};

function buildSourceImpactRows(
  missing: ConnectorStatus[],
  stale: ConnectorStatus[],
  outsideDailyScope: ConnectorStatus[]
): SourceImpactRow[] {
  const missingRows = missing.map((connector) => ({
    id: `missing-${connector.id}`,
    source: connector.label,
    blocked: sourceBlockedDecisionLabel(connector),
    impact: sourceDecisionImpactLabel(connector),
    nextStep: sourceRepairStepLabel(connector),
    dotClass: "bg-risk"
  }));
  const staleRows = stale.map((connector) => ({
    id: `stale-${connector.id}`,
    source: connector.label,
    blocked: sourceStaleDecisionLabel(connector),
    impact: "Decyzja wymaga świeżego odczytu przed wnioskiem",
    nextStep: "Odśwież źródło przed decyzją",
    dotClass: "bg-wait"
  }));
  const outsideRow =
    outsideDailyScope.length > 0
      ? [
          {
            id: "outside-daily-scope",
            source: "Inne poza zakresem",
            blocked: `Dane z ${outsideDailyScope.length} ${pluralize(
              outsideDailyScope.length,
              "źródła",
              "źródeł",
              "źródeł"
            )} pomijane w dziennym zakresie`,
            impact: "Ograniczony wgląd w nieujęte kanały",
            nextStep: "Zostaw poza planem dnia albo włącz zakres",
            dotClass: "bg-wait"
          }
        ]
      : [];
  if (missingRows.length === 0 && staleRows.length === 0 && outsideRow.length === 0) {
    return [
      {
        id: "sources-ready",
        source: "Brak krytycznych braków",
        blocked: "Główne źródła mogą zasilać decyzje po sprawdzeniu świeżości danych",
        impact: "Decyzje nie są blokowane przez dostęp",
        nextStep: "Pracuj dalej i pilnuj świeżości",
        dotClass: "bg-success"
      }
    ];
  }
  return [...missingRows, ...staleRows, ...outsideRow];
}

function sourceBlockedDecisionLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  const label = connector.label;
  if (id.includes("linkedin")) return "Reklamy LinkedIn, zasięgi, zaangażowanie, leady";
  if (id.includes("facebook")) return "Posty, zasięgi, zaangażowanie, wyniki kampanii";
  if (id.includes("google_ads")) return "Kampanie, rekomendacje, search terms i bezpieczne akcje Ads";
  if (id.includes("analytics") || id.includes("ga4")) return "Ocena jakości ruchu, konwersji i zdarzeń";
  if (id.includes("merchant")) return "Feed produktowy, status produktów i widoczność Shopping/PMax";
  if (id.includes("wordpress")) return "Treści, publikacje i sprawdzenie istniejących stron";
  return `${label}: decyzje zależne od tego źródła`;
}

function sourceDecisionImpactLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("linkedin")) return "Brak pełnego obrazu działań w kanałach B2B";
  if (id.includes("facebook")) return "Niepełna ocena skuteczności komunikacji";
  if (id.includes("google_ads")) return "Blokada pełnej oceny Ads i zmian kampanii";
  if (id.includes("analytics") || id.includes("ga4")) return "Nie wolno oceniać efektu kampanii bez pomiaru";
  if (id.includes("merchant")) return "Nie wolno oceniać gotowości produktów bez danych pliku produktowego";
  if (id.includes("wordpress")) return "Ryzyko duplikacji i pracy na nieaktualnym spisie treści";
  return "Decyzje z tego kanału pozostają zablokowane albo zdegradowane";
}

function sourceRepairStepLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("linkedin")) return "Podłącz LinkedIn albo zostaw social jako review-only";
  if (id.includes("facebook")) return "Podłącz Facebook Pages albo pomiń ten kanał";
  if (id.includes("google_ads")) return "Uzupełnij dostęp Ads i odśwież źródło";
  if (id.includes("analytics") || id.includes("ga4")) return "Uzupełnij GA4 i sprawdź pomiar";
  if (id.includes("merchant")) return "Uzupełnij Merchant i odśwież feed";
  if (id.includes("wordpress")) return "Uzupełnij WordPress i pobierz spis treści";
  return "Uzupełnij dostęp i odśwież źródło";
}

function sourceStaleDecisionLabel(connector: ConnectorStatus) {
  const id = connector.id.toLowerCase();
  if (id.includes("google_ads")) return "Aktualna ocena kampanii, kosztów i rekomendacji";
  if (id.includes("analytics") || id.includes("ga4")) return "Aktualna ocena jakości ruchu i pomiaru";
  if (id.includes("merchant")) return "Aktualny status pliku produktowego, produktów i atrybutów";
  if (id.includes("search_console")) return "Aktualne decyzje SEO z GSC";
  if (id.includes("wordpress")) return "Aktualny spis treści i ryzyko duplikacji";
  if (id.includes("ahrefs")) return "Aktualne luki SEO i konkurencja";
  if (id.includes("localo")) return "Aktualna widoczność lokalna";
  return `${connector.label}: decyzje wymagają świeżego odczytu`;
}

function formatConnectorList(connectors: ConnectorStatus[]) {
  if (connectors.length === 1) return connectors[0].label;
  if (connectors.length === 2) return `${connectors[0].label} i ${connectors[1].label}`;
  return `${connectors.slice(0, -1).map((connector) => connector.label).join(", ")} i ${
    connectors[connectors.length - 1].label
  }`;
}

function pluralize(count: number, one: string, few: string, many: string) {
  if (count === 1) return one;
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14)) return few;
  return many;
}

export function SectionHeading({ title }: { title: string }) {
  return <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-slate-600">{title}</h2>;
}

function DetailToggle({
  expanded,
  label,
  onClick
}: {
  expanded: boolean;
  label: string;
  onClick: () => void;
}) {
  const Icon = expanded ? ChevronDown : ChevronRight;
  return (
    <button
      type="button"
      aria-expanded={expanded}
      onClick={onClick}
      className="inline-flex min-h-9 items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
    >
      <Icon aria-hidden="true" size={16} />
      {label}
    </button>
  );
}
