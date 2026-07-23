import { useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState } from "react";

import {
  getContentWorkflowEntry,
  type ContentInventoryCatalogResponse,
  type ContentWorkflowEntryResponse
} from "../lib/api";

export function ContentWorkflowEntryPanel({
  entry,
  inventory,
  browseInventory,
  newPageOpen,
  onBrowseInventory,
  onCloseSecondaryView,
  onOpenNewPage,
  onSelectWorkItem
}: {
  entry: ContentWorkflowEntryResponse;
  inventory: ContentInventoryCatalogResponse | null;
  browseInventory: boolean;
  newPageOpen: boolean;
  onBrowseInventory: () => void;
  onCloseSecondaryView: () => void;
  onOpenNewPage: () => void;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (newPageOpen) {
    return <ContentWorkflowNewPageStart onReturn={onCloseSecondaryView} />;
  }
  if (browseInventory) {
    return <ContentWorkflowInventoryBrowse inventory={inventory} onReturn={onCloseSecondaryView} onSelectWorkItem={onSelectWorkItem} />;
  }
  return <ContentWorkflowIntentStart entry={entry} onBrowseInventory={onBrowseInventory} onOpenNewPage={onOpenNewPage} onSelectWorkItem={onSelectWorkItem} />;
}

function ContentWorkflowIntentStart({
  entry,
  onBrowseInventory,
  onOpenNewPage,
  onSelectWorkItem
}: {
  entry: ContentWorkflowEntryResponse;
  onBrowseInventory: () => void;
  onOpenNewPage: () => void;
  onSelectWorkItem: (workItemId: string) => void;
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
              {entry.recommendations.map((recommendation) => (
                <article key={recommendation.work_item_id} className="flex min-h-60 flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_16px_42px_-34px_rgba(15,23,42,0.5)]">
                  <p className="text-[11px] font-bold uppercase tracking-[0.13em] text-action">Proponowana praca</p>
                  <h3 className="mt-3 text-lg font-semibold leading-6 text-ink">{recommendation.title}</h3>
                  <p className="mt-2 line-clamp-2 text-xs text-slate-500">{recommendation.url}</p>
                  <p className="mt-4 text-sm leading-6 text-slate-700">{recommendation.reason}</p>
                  <dl className="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
                    {recommendation.facts.map((fact) => <div key={fact.label}><dt className="font-semibold text-slate-500">{fact.label}</dt><dd className="mt-0.5 text-slate-700">{fact.value}</dd></div>)}
                  </dl>
                  <button type="button" className="mt-auto pt-5 text-left text-sm font-semibold text-action hover:text-action/80" onClick={() => onSelectWorkItem(recommendation.work_item_id)}>Otwórz stronę <span aria-hidden="true">→</span></button>
                </article>
              ))}
            </div>
          ) : <p className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600">Nie ma teraz rekomendacji opartych na wystarczających danych. Możesz wyszukać stronę lub przejrzeć cały serwis.</p>}
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600">
          Dane w tym miejscu służą tylko do odczytu. Wybranie strony nie zmienia treści ani nie publikuje niczego.
        </section>
      </div>
    </main>
  );
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

function ContentWorkflowNewPageStart({ onReturn }: { onReturn: () => void }) {
  return <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_#e7f8ee,_transparent_32%),linear-gradient(180deg,_#fbfdff_0%,_#ffffff_58%)] px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-new-page-start"><div className="mx-auto max-w-4xl"><button type="button" className="text-sm font-semibold text-action" onClick={onReturn}>← Wróć do wyboru pracy</button><section className="mt-6 rounded-2xl border border-emerald-200 bg-white p-6 shadow-[0_18px_48px_-36px_rgba(15,23,42,0.55)] lg:p-9"><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700">Nowa strona</p><h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">Zaczynamy od briefu, nie od adresu</h1><p className="mt-4 max-w-2xl text-sm leading-7 text-slate-700">W kolejnym etapie określisz cel strony, usługę, odbiorcę, intencję i jej miejsce w serwisie. Zanim dokument trafi do review, WILQ sprawdzi też pokrycie istniejących treści.</p><div className="mt-7 grid gap-3 sm:grid-cols-2"><InfoTile label="Potrzebne w briefie" value="cel, usługa, odbiorca, intencja i miejsce w serwisie" /><InfoTile label="Nie jest potrzebne teraz" value="stary URL, docelowy post WordPressa ani układ ACF" /></div><p className="mt-7 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm leading-6 text-emerald-950">Brief nowej strony zostanie zapisany w następnym etapie. Samo wejście tutaj niczego nie tworzy ani nie publikuje.</p></section></div></main>;
}

function ContentWorkflowInventoryBrowse({ inventory, onReturn, onSelectWorkItem }: { inventory: ContentInventoryCatalogResponse | null; onReturn: () => void; onSelectWorkItem: (workItemId: string) => void }) {
  const [filter, setFilter] = useState("");
  const items = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase("pl-PL");
    return (inventory?.items ?? []).filter((item) => !query || `${item.title ?? ""} ${item.path} ${item.url}`.toLocaleLowerCase("pl-PL").includes(query));
  }, [filter, inventory]);
  return <main className="min-h-screen bg-slate-50 px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-inventory"><div className="mx-auto max-w-6xl"><button type="button" className="text-sm font-semibold text-action" onClick={onReturn}>← Wróć do wyboru pracy</button><section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-action">Przeglądaj cały serwis</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Publiczne strony do odświeżenia</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">To jest katalog adresów publicznych. Nie potwierdza typu wpisu, układu WordPressa ani możliwości zapisu.</p><input type="search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Szukaj tytułu lub adresu" className="mt-5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-action focus:bg-white" /></section>{inventory ? <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white"><p className="border-b border-slate-100 px-5 py-3 text-sm text-slate-600">Wyniki: {items.length} z {inventory.total_count} adresów</p><div className="divide-y divide-slate-100">{items.map((item) => <button key={item.catalog_id} type="button" className="flex w-full flex-wrap items-center justify-between gap-3 px-5 py-4 text-left hover:bg-slate-50" onClick={() => onSelectWorkItem(item.work_item_id)}><span><span className="block font-semibold text-ink">{item.title || item.path}</span><span className="mt-1 block text-xs text-slate-500">{item.url}</span></span><span className="text-sm font-semibold text-action">Otwórz stronę →</span></button>)}{!items.length ? <p className="px-5 py-6 text-sm text-slate-600">Nie znaleziono pasujących stron.</p> : null}</div></section> : <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">Wczytuję katalog stron…</section>}</div></main>;
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 text-sm leading-6 text-slate-700">{value}</p></div>;
}
