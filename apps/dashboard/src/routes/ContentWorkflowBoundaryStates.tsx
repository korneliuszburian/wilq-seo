import type {
  ContentInventoryCatalogResponse,
  ContentWorkItemQueueCandidate,
  ContentWorkItemQueueResponse
} from "../lib/api";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";

export type ContentSourceRefreshControl = {
  active: boolean;
  status: "idle" | "loading" | "success" | "error";
  summary: string;
  error: string | null;
  onRefresh: (url: string) => void;
};

export function ContentFreshnessBanner({
  assessment,
  refresh,
  refreshTargetUrl
}: {
  assessment: ContentWorkItemQueueResponse["freshness_assessment"];
  refresh?: ContentSourceRefreshControl;
  refreshTargetUrl?: string | null;
}) {
  const qualityLabels: Record<string, string> = {
    google_search_console: "GSC",
    google_analytics_4: "GA4",
    google_ads: "Ads",
    ahrefs: "Ahrefs",
    localo: "Localo",
    wordpress_ekologus: "WordPress"
  };
  const qualityStates = assessment.connector_quality_states ?? {};
  const settlementStates = assessment.connector_settlement_states ?? {};
  const qualityWarnings = Object.entries(qualityStates)
    .filter(([, state]) => state !== "verified" && state !== "unknown")
    .map(([connector, state]) => `${qualityLabels[connector] ?? connector}: ${state === "partial" ? "częściowy odczyt" : "jakość do sprawdzenia"}`);
  const settlementWarnings = Object.entries(settlementStates)
    .filter(([, state]) => state === "settling")
    .filter(([connector]) => !qualityWarnings.some((warning) => warning.startsWith(`${qualityLabels[connector] ?? connector}:`)))
    .map(([connector]) => `${qualityLabels[connector] ?? connector}: dane się rozliczają`);
  const sourceWarnings = [...qualityWarnings, ...settlementWarnings];
  if (!assessment.requires_refresh && !sourceWarnings.length) return null;
  return (
    <section className="mb-4 rounded-md border border-wait/30 bg-wait/10 p-4" role="status">
      <h2 className="text-sm font-semibold text-wait">
        Źródła treści: {assessment.state_label}
      </h2>
      <p className="mt-2 hidden text-sm leading-6 text-slate-700 sm:block">{assessment.summary}</p>
      <p className="mt-2 line-clamp-3 text-xs font-semibold leading-5 text-ink sm:text-sm sm:leading-6">
        Następny bezpieczny krok: {assessment.next_step}
      </p>
      {sourceWarnings.length ? (
        <p className="mt-2 text-xs leading-5 text-slate-600" data-testid="source-quality-warning">
          Jakość źródeł: {sourceWarnings.join(" · ")}. To sygnał interpretacyjny, nie wynik kampanii.
        </p>
      ) : null}
      {refresh && refreshTargetUrl && assessment.stale_connector_ids.length ? (
        <div className="mt-3 flex flex-wrap items-center gap-2" data-testid="content-source-refresh">
          {assessment.stale_connector_ids.map((connectorId) => {
            return (
              <div key={connectorId} className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  className="rounded-md border border-action/30 bg-white px-3 py-2 text-xs font-semibold text-action hover:bg-action/5 disabled:cursor-wait disabled:opacity-60"
                  disabled={refresh.active}
                  onClick={() => refresh.onRefresh(refreshTargetUrl)}
                >
                  {refresh.active ? "Sprawdzanie strony…" : "Sprawdź stronę ponownie"}
                </button>
                {refresh.status === "success" ? <span className="text-xs text-slate-600">{refresh.summary}</span> : null}
                {refresh.error ? <span className="text-xs font-semibold text-wait">{refresh.error}</span> : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

export function ContentWorkflowError() {
  return <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8"><div className="rounded-md border border-wait/30 bg-wait/10 p-4 text-sm text-wait">Nie udało się odczytać workflow treści z WILQ. Nie pokazujemy decyzji bez kontraktów API.</div></main>;
}

export function ContentWorkflowEmptyQueue({ queue }: { queue: ContentWorkItemQueueResponse }) {
  return <main className="w-full px-4 py-5 lg:px-7 2xl:px-8"><ContentWorkflowWorkspaceHeader /><section className="rounded-md border border-wait/30 bg-wait/10 p-4"><h2 className="text-sm font-semibold uppercase tracking-normal text-wait">Brak propozycji do pracy nad treścią</h2><p className="mt-2 text-sm leading-6 text-slate-700">{queue.operator_summary}</p></section></main>;
}

export function ContentWorkflowSelectedLoading({
  candidate,
  error = false
}: {
  candidate: ContentWorkItemQueueCandidate;
  error?: boolean;
}) {
  const pageLabel = workflowLoadingPageLabel(candidate);
  return (
    <main className="w-full px-4 py-5 lg:px-7 2xl:px-8">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-md border border-line bg-white p-4 shadow-sm" aria-live="polite">
        <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Wybrana strona</p>
        <h2 className="mt-1 text-2xl font-semibold text-ink">{pageLabel}</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          {error
            ? "Nie udało się odczytać aktualnego workflow. Odśwież stronę, aby spróbować ponownie."
            : "Wczytuję aktualny plan, wersję roboczą i ograniczenia dla tej strony…"}
        </p>
      </section>
    </main>
  );
}

function workflowLoadingPageLabel(candidate: ContentWorkItemQueueCandidate): string {
  if (!candidate.final_canonical_url) return candidate.title;
  try {
    return new URL(candidate.final_canonical_url).pathname || candidate.title;
  } catch {
    return candidate.title;
  }
}

export function ContentWorkflowInventorySelectionLoading({
  item
}: {
  item: ContentInventoryCatalogResponse["items"][number];
}) {
  return (
    <main className="w-full px-4 py-5 lg:px-7 2xl:px-8">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-md border border-line bg-white p-4 shadow-sm" aria-live="polite">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Wybrana strona</p>
            <h1 className="mt-1 text-2xl font-semibold text-ink">{item.title ?? item.path}</h1>
            <p className="mt-2 break-all text-sm text-slate-600">{item.url}</p>
          </div>
          <span className="rounded-md border border-action/30 bg-action/10 px-3 py-2 text-xs font-semibold text-action">
            {item.content_type}
          </span>
        </div>
        <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-md border border-line bg-surface p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">Materiał</div>
            <p className="mt-1 text-slate-700">{inventoryMaterialLabel(item.material_status)}</p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">Metryki</div>
            <p className="mt-1 text-slate-700">
              {item.metrics_status === "available"
                ? `${item.metrics_clicks.toLocaleString("pl-PL")} kliknięć · ${item.metrics_impressions.toLocaleString("pl-PL")} wyświetleń`
                : "brak świeżych danych"}
            </p>
          </div>
          <div className="rounded-md border border-line bg-surface p-3">
            <div className="text-xs font-semibold uppercase tracking-normal text-slate-500">Następny krok</div>
            <p className="mt-1 text-slate-700">Ładujemy decyzję i dopasowane źródła.</p>
          </div>
        </div>
        <p className="mt-4 rounded-md border border-line bg-white px-3 py-3 text-sm text-slate-600">
          Strona jest już rozpoznana z aktualnego inventory WordPress. Szczegóły decyzji i etapów doładują się poniżej.
        </p>
      </section>
    </main>
  );
}

function inventoryMaterialLabel(status: ContentInventoryCatalogResponse["items"][number]["material_status"]) {
  switch (status) {
    case "content_and_structure":
      return "treść i struktura";
    case "content_summary":
      return "podsumowanie treści";
    case "structure_only":
      return "sama struktura";
    default:
      return "tylko adres";
  }
}
