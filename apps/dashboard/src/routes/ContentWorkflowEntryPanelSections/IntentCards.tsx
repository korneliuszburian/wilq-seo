import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useState } from "react";

import {
  getContentWorkflowEntry,
  type ContentDiagnosticsResponse,
  type ContentWorkflowEntryResponse
} from "../../lib/api";
import { ContentRequiredSourceRefresh } from "../ContentRequiredSourceRefresh";

export function ContentWorkflowIntentStart({
  entry,
  diagnostics,
  onBrowseInventory,
  onOpenNewPage,
  onSelectWorkItem,
  onSourcesRefreshed
}: {
  entry: ContentWorkflowEntryResponse;
  diagnostics: ContentDiagnosticsResponse | null;
  onBrowseInventory: () => void;
  onOpenNewPage: () => void;
  onSelectWorkItem: (workItemId: string) => void;
  onSourcesRefreshed: () => void;
}) {
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search.trim());
  const searchResults = useQuery({
    queryKey: ["content-workflow", "entry", "search", deferredSearch],
    queryFn: () => getContentWorkflowEntry(deferredSearch),
    enabled: deferredSearch.length > 1,
    staleTime: 30_000
  });

  return (
    <main className="min-h-screen w-full bg-[radial-gradient(circle_at_top_right,_#e6f3ff,_transparent_32%),radial-gradient(circle_at_25%_10%,_#f0fdf4,_transparent_28%),linear-gradient(180deg,_#fbfdff_0%,_#ffffff_58%)] px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-entry">
      <div className="mx-auto max-w-7xl">
        <header className="max-w-3xl">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-action">Treści i SEO</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink lg:text-5xl">Tworzenie i odświeżanie treści</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 lg:text-base">
            Zacznij od tego, co chcesz osiągnąć. WILQ pomoże Ci pracować na aktualnej stronie albo przygotować brief zupełnie nowej.
          </p>
        </header>

        <section className="mt-8" aria-labelledby="content-workflow-intent-heading">
          <h2 id="content-workflow-intent-heading" className="text-xl font-semibold text-ink">Co chcesz zrobić?</h2>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <IntentCard
              eyebrow="Istniejąca strona"
              title={entry.refresh_existing.label}
              description={entry.refresh_existing.description}
              action="Wybierz stronę"
              tone="blue"
              onClick={() => document.getElementById("content-workflow-entry-search")?.focus()}
            />
            <IntentCard
              eyebrow="Nowy temat"
              title={entry.new_page.label}
              description={entry.new_page.description}
              action="Zacznij od briefu"
              tone="green"
              onClick={onOpenNewPage}
            />
          </div>
        </section>

        <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_16px_42px_-34px_rgba(15,23,42,0.45)] lg:p-5" aria-labelledby="content-workflow-search-heading">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <h2 id="content-workflow-search-heading" className="text-lg font-semibold text-ink">Odśwież istniejącą stronę</h2>
              <p className="mt-1 text-sm text-slate-600">Wyszukaj publiczną stronę, usługę lub temat. Wybór nie oznacza jeszcze przygotowania do WordPressa.</p>
            </div>
          </div>
          <label className="mt-4 block" htmlFor="content-workflow-entry-search">
            <span className="sr-only">Szukaj strony, usługi lub tematu</span>
            <input
              id="content-workflow-entry-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="np. BDO, operat wodnoprawny, doradztwo środowiskowe"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-ink outline-none transition focus:border-action focus:bg-white focus:ring-4 focus:ring-action/10"
            />
          </label>
          {deferredSearch.length > 1 ? <EntrySearchResults loading={searchResults.isLoading} error={searchResults.isError} entry={searchResults.data ?? null} onSelectWorkItem={onSelectWorkItem} /> : null}
        </section>

        <section className="mt-8" aria-labelledby="content-workflow-recommendations-heading">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 id="content-workflow-recommendations-heading" className="text-xl font-semibold text-ink">Do pracy teraz</h2>
              <p className="mt-1 text-sm text-slate-600">Wybrane sprawy, dla których WILQ ma konkretny powód do sprawdzenia.</p>
            </div>
            <button type="button" className="text-sm font-semibold text-action hover:text-action/80" onClick={onBrowseInventory}>{entry.browse_inventory_label} <span aria-hidden="true">→</span></button>
          </div>
          {entry.recommendations.length ? (
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              {entry.recommendations.map((recommendation) => {
                const firstBlocker = recommendation.blockers[0];
                const doItNow = recommendation.decision_action === "do_it_now";
                const decisionLabel = recommendation.decision_mode === "block" && firstBlocker
                  ? firstBlocker.label
                  : recommendation.decision_label;
                return (
                  <article key={recommendation.work_item_id} className="flex min-h-60 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_16px_42px_-34px_rgba(15,23,42,0.5)]">
                    <p className={`rounded-lg border px-3 py-2 text-sm font-semibold ${doItNow ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-wait/30 bg-wait/10 text-wait"}`}>
                      {doItNow ? "Zrób teraz" : "Nie teraz"}: {decisionLabel}
                    </p>
                    {firstBlocker ? <p className="mt-2 text-xs font-semibold leading-5 text-wait">Brakuje: {firstBlocker.label}</p> : null}
                    <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.13em] text-action">Proponowana praca</p>
                    <h3 className="mt-3 text-lg font-semibold leading-6 text-ink">{recommendation.title}</h3>
                    <p className="mt-2 line-clamp-2 text-xs text-slate-500">{recommendation.url}</p>
                    <p className="mt-4 text-sm leading-6 text-slate-700">{recommendation.reason}</p>
                    <dl className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
                      {recommendation.facts.map((fact) => <div key={fact.label}><dt className="font-semibold text-slate-500">{fact.label}{fact.period_label ? ` (${fact.period_label})` : ""}</dt><dd className="mt-0.5 text-slate-700">{fact.value}</dd></div>)}
                    </dl>
                    <button type="button" className="mt-auto pt-5 text-left text-sm font-semibold text-action hover:text-action/80" onClick={() => onSelectWorkItem(recommendation.work_item_id)}>Otwórz stronę <span aria-hidden="true">→</span></button>
                  </article>
                );
              })}
            </div>
          ) : <ContentWorkflowEmptyRecommendations diagnostics={diagnostics} onSourcesRefreshed={onSourcesRefreshed} />}
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600">
          Dane w tym miejscu służą tylko do odczytu. Wybranie strony nie zmienia treści ani nie publikuje niczego.
        </section>
      </div>
    </main>
  );
}

function ContentWorkflowEmptyRecommendations({
  diagnostics,
  onSourcesRefreshed
}: {
  diagnostics: ContentDiagnosticsResponse | null;
  onSourcesRefreshed: () => void;
}) {
  const decision = diagnostics?.marketer_decision;
  if (decision?.status !== "blocked") {
    return <p className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600">Nie ma teraz rekomendacji opartych na wystarczających danych. Możesz wyszukać stronę lub przejrzeć cały serwis.</p>;
  }
  if (!diagnostics) return null;
  const connectorIds = [...new Set([
    ...diagnostics.freshness_assessment.missing_connector_ids,
    ...diagnostics.freshness_assessment.stale_connector_ids
  ])];
  const connectorLabels = Object.fromEntries(
    diagnostics.connectors.map((connector) => [connector.id, connector.label])
  );
  return <section className="mt-4 rounded-2xl border border-wait/30 bg-wait/5 p-5 text-sm text-ink" data-testid="content-workflow-data-blocker">
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-wait">Blokada danych</p>
    <h3 className="mt-2 text-lg font-semibold">{decision.decision}</h3>
    <p className="mt-2 leading-6 text-slate-700">{decision.why_it_matters}</p>
    <p className="mt-3 font-semibold leading-6 text-slate-800">Co możesz zrobić teraz: {decision.safe_next_action}</p>
    {decision.source_connector_labels.length ? <p className="mt-3 text-xs leading-5 text-slate-600">Źródła wymagające odczytu: {decision.source_connector_labels.join(", ")}</p> : null}
    {decision.evidence_ids.length ? <p className="mt-2 text-xs leading-5 text-slate-600">Dowody źródłowe są dostępne w szczegółach pracy.</p> : null}
    <ContentRequiredSourceRefresh
      connectorIds={connectorIds}
      connectorLabels={connectorLabels}
      onCompleted={onSourcesRefreshed}
    />
  </section>;
}

function IntentCard({ eyebrow, title, description, action, tone, onClick }: { eyebrow: string; title: string; description: string; action: string; tone: "blue" | "green"; onClick: () => void }) {
  const palette = tone === "blue" ? "border-action/35 bg-[linear-gradient(135deg,_#f5f9ff,_#ffffff_62%)]" : "border-emerald-200 bg-[linear-gradient(135deg,_#f4fcf5,_#ffffff_62%)]";
  const accent = tone === "blue" ? "text-action" : "text-emerald-700";
  return <button type="button" className={`group rounded-2xl border p-6 text-left shadow-[0_16px_42px_-34px_rgba(15,23,42,0.5)] transition hover:-translate-y-0.5 hover:shadow-[0_20px_46px_-32px_rgba(15,23,42,0.6)] ${palette}`} onClick={onClick}>
    <p className={`text-[11px] font-bold uppercase tracking-[0.16em] ${accent}`}>{eyebrow}</p>
    <h3 className="mt-3 text-2xl font-semibold tracking-tight text-ink">{title}</h3>
    <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">{description}</p>
    <span className={`mt-6 inline-flex items-center gap-2 text-sm font-semibold ${accent}`}>{action} <span className="transition group-hover:translate-x-1" aria-hidden="true">→</span></span>
  </button>;
}

function EntrySearchResults({ loading, error, entry, onSelectWorkItem }: { loading: boolean; error: boolean; entry: ContentWorkflowEntryResponse | null; onSelectWorkItem: (workItemId: string) => void }) {
  if (loading) return <p className="mt-3 text-sm text-slate-600">Szukam stron w publicznym katalogu…</p>;
  if (error) return <p className="mt-3 text-sm text-wait">Nie udało się wyszukać stron. Spróbuj ponownie.</p>;
  if (!entry?.search_results.length) return <p className="mt-3 text-sm text-slate-600">Nie znaleziono strony pasującej do wyszukiwania.</p>;
  return <div className="mt-3 divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white">
    {entry.search_results.map((result) => <button key={result.work_item_id} type="button" className="flex w-full flex-wrap items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50" onClick={() => onSelectWorkItem(result.work_item_id)}><span><span className="block font-semibold text-ink">{result.title}</span><span className="mt-1 block text-xs text-slate-500">{result.url}</span></span><span className="text-xs font-medium text-slate-600">{result.material_label} <span className="ml-2 text-action" aria-hidden="true">→</span></span></button>)}
  </div>;
}
