import { useMutation, useQuery } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState, type ReactNode } from "react";

import {
  getContentWorkflowEntry,
  createContentNewPageBrief,
  getContentNewPageBriefWorkspace,
  type ContentInventoryCatalogResponse,
  type ContentNewPageBriefInput,
  type ContentNewPageBriefWorkspace,
  type ContentWorkflowEntryResponse
} from "../lib/api";

export function ContentWorkflowEntryPanel({
  entry,
  inventory,
  browseInventory,
  newPageOpen,
  newPageId,
  onBrowseInventory,
  onCloseSecondaryView,
  onOpenNewPage,
  onNewPageBriefSaved,
  onSelectWorkItem
}: {
  entry: ContentWorkflowEntryResponse;
  inventory: ContentInventoryCatalogResponse | null;
  browseInventory: boolean;
  newPageOpen: boolean;
  newPageId: string | null;
  onBrowseInventory: () => void;
  onCloseSecondaryView: () => void;
  onOpenNewPage: () => void;
  onNewPageBriefSaved: (briefId: string) => void;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (newPageOpen) {
    return <ContentWorkflowNewPageBrief briefId={newPageId === "1" ? null : newPageId} onReturn={onCloseSecondaryView} onSaved={onNewPageBriefSaved} />;
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

function ContentWorkflowNewPageBrief({ briefId, onReturn, onSaved }: { briefId: string | null; onReturn: () => void; onSaved: (briefId: string) => void }) {
  const savedBrief = useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId],
    queryFn: () => getContentNewPageBriefWorkspace(briefId ?? ""),
    enabled: Boolean(briefId),
    staleTime: 30_000
  });
  const [form, setForm] = useState<ContentNewPageBriefInput>({
    title: "", purpose: "", service: "", audience: "", search_intent: "", proposed_ia_location: ""
  });
  const saveBrief = useMutation({
    mutationFn: createContentNewPageBrief,
    onSuccess: (workspace) => onSaved(workspace.brief.brief_id)
  });
  const workspace = savedBrief.data;
  if (briefId && savedBrief.isLoading) return <NewPageShell onReturn={onReturn}><p className="text-sm text-slate-600">Wczytuję zapisany brief…</p></NewPageShell>;
  if (briefId && (savedBrief.error || !workspace)) return <NewPageShell onReturn={onReturn}><p className="rounded-xl border border-wait/30 bg-white px-4 py-3 text-sm text-ink">Nie udało się odczytać briefu. Wróć do wyboru i spróbuj ponownie.</p></NewPageShell>;
  if (workspace) return <NewPageSaved workspace={workspace} onReturn={onReturn} />;
  return <NewPageShell onReturn={onReturn}>
    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700">Nowa strona</p>
    <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">Zacznij od briefu nowej strony</h1>
    <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-700">Nie potrzebujesz starego adresu ani miejsca w WordPressie. Opisz planowaną stronę, a WILQ sprawdzi jej pokrycie w aktualnym serwisie.</p>
    <form className="mt-7 grid gap-4" onSubmit={(event) => { event.preventDefault(); saveBrief.mutate(form); }}>
      <BriefField label="Roboczy tytuł strony" value={form.title} onChange={(title) => setForm({ ...form, title })} placeholder="np. Audyt środowiskowy dla inwestycji" />
      <BriefField label="Cel strony" value={form.purpose} onChange={(purpose) => setForm({ ...form, purpose })} placeholder="Co ta strona ma pomóc odbiorcy zrozumieć lub zrobić?" multiline />
      <div className="grid gap-4 md:grid-cols-2"><BriefField label="Usługa" value={form.service} onChange={(service) => setForm({ ...form, service })} placeholder="np. Dokumentacja środowiskowa" /><BriefField label="Odbiorca" value={form.audience} onChange={(audience) => setForm({ ...form, audience })} placeholder="np. Inwestor planujący przedsięwzięcie" /></div>
      <div className="grid gap-4 md:grid-cols-2"><BriefField label="Intencja wyszukiwania" value={form.search_intent} onChange={(search_intent) => setForm({ ...form, search_intent })} placeholder="Jakiego problemu szuka odbiorca?" /><BriefField label="Miejsce w serwisie" value={form.proposed_ia_location} onChange={(proposed_ia_location) => setForm({ ...form, proposed_ia_location })} placeholder="np. Usługi → Dokumentacja środowiskowa" /></div>
      {saveBrief.error ? <p className="text-sm text-wait">Nie udało się zapisać briefu. Uzupełnij wymagane pola i spróbuj ponownie.</p> : null}
      <div className="flex flex-wrap items-center gap-3"><button type="submit" disabled={saveBrief.isPending} className="rounded-xl bg-action px-5 py-3 text-sm font-semibold text-white disabled:opacity-60">{saveBrief.isPending ? "Zapisuję brief…" : "Zapisz brief i sprawdź pokrycie"}</button><p className="text-xs leading-5 text-slate-600">To nie tworzy dokumentu, rewizji ani niczego w WordPressie.</p></div>
    </form>
  </NewPageShell>;
}

function NewPageSaved({ workspace, onReturn }: { workspace: ContentNewPageBriefWorkspace; onReturn: () => void }) {
  const guard = workspace.overlap_guard;
  return <NewPageShell onReturn={onReturn}>
    <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-700">Brief nowej strony</p>
    <h1 className="mt-3 text-3xl font-semibold tracking-tight text-ink">{workspace.brief.title}</h1>
    <p className="mt-3 text-sm leading-7 text-slate-700">Brief jest zapisany. To nadal plan nowej strony, nie dokument do publikacji ani układ WordPressa.</p>
    <dl className="mt-6 grid gap-3 sm:grid-cols-2"><InfoTile label="Cel" value={workspace.brief.purpose} /><InfoTile label="Usługa" value={workspace.brief.service} /><InfoTile label="Odbiorca" value={workspace.brief.audience} /><InfoTile label="Miejsce w serwisie" value={workspace.brief.proposed_ia_location} /></dl>
    <section className="mt-7 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-800">Pokrycie istniejących treści</p><h2 className="mt-2 text-xl font-semibold text-ink">{guard.label}</h2><p className="mt-2 text-sm leading-6 text-slate-700">{guard.reason}</p>{guard.candidates.length ? <ul className="mt-4 space-y-2">{guard.candidates.map((candidate) => <li key={`${candidate.url}-${candidate.match_kind}`} className="rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm"><span className="font-semibold text-ink">{candidate.title}</span><span className="block text-xs text-slate-600">{candidate.url}</span></li>)}</ul> : null}<p className="mt-4 text-xs leading-5 text-slate-600">{guard.caveat}</p></section>
    <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Co dalej?</h2><p className="mt-2 text-sm leading-6 text-slate-700">{workspace.review_reason}</p><p className="mt-3 text-sm font-semibold text-slate-700">{workspace.next_action_label}</p></section>
  </NewPageShell>;
}

function NewPageShell({ onReturn, children }: { onReturn: () => void; children: ReactNode }) {
  return <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_#e7f8ee,_transparent_32%),linear-gradient(180deg,_#fbfdff_0%,_#ffffff_58%)] px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-new-page-brief"><div className="mx-auto max-w-4xl"><button type="button" className="text-sm font-semibold text-action" onClick={onReturn}>← Wróć do wyboru pracy</button><section className="mt-6 rounded-2xl border border-emerald-200 bg-white p-6 shadow-[0_18px_48px_-36px_rgba(15,23,42,0.55)] lg:p-9">{children}</section></div></main>;
}

function BriefField({ label, value, onChange, placeholder, multiline = false }: { label: string; value: string; onChange: (value: string) => void; placeholder: string; multiline?: boolean }) {
  const className = "mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm text-ink outline-none focus:border-action focus:bg-white focus:ring-4 focus:ring-action/10";
  return <label className="block text-sm font-semibold text-ink"><span>{label}</span>{multiline ? <textarea required value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} rows={3} className={className} /> : <input required value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className={className} />}</label>;
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
