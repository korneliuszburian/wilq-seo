import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useDeferredValue, useMemo, useState, type ReactNode } from "react";

import {
  getContentWorkflowEntry,
  createContentNewPageBrief,
  createContentNewPageFoundation,
  createContentNewPagePlanningProposal,
  createContentNewPageInitialDraft,
  createContentNewPageDeliveryAction,
  getContentNewPageBriefWorkspace,
  getContentNewPageCanonicalDocument,
  getContentNewPageDeliveryReadiness,
  getContentNewPagePlanningProposal,
  getContentRevisionPublicDeployment,
  postContentRevisionPublicDeployment,
  postContentWorkItemLearningProposal,
  postContentWorkItemMeasurementOutcome,
  postContentWorkItemMeasurementWindow,
  reviewContentNewPagePlanning,
  reviewContentNewPageRevision,
  type ContentDiagnosticsResponse,
  type ContentNewPageCanonicalDocumentWorkspace,
  type ContentNewPageDeliveryReadiness,
  type ContentPublicDeploymentReadResponse,
  type ContentInventoryCatalogResponse,
  type ContentNewPageBriefInput,
  type ContentNewPageBriefWorkspace,
  type ContentPlanningProposal,
  type ContentWorkflowEntryResponse
} from "../lib/api";

export function ContentWorkflowEntryPanel({
  entry,
  inventory,
  diagnostics,
  browseInventory,
  newPageOpen,
  newPageId,
  onBrowseInventory,
  onCloseSecondaryView,
  onOpenNewPage,
  onNewPageBriefSaved,
  onSelectWorkItem
}: {
  entry: ContentWorkflowEntryResponse | null;
  inventory: ContentInventoryCatalogResponse | null;
  diagnostics: ContentDiagnosticsResponse | null;
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
  if (!entry) return null;
  return <ContentWorkflowIntentStart entry={entry} diagnostics={diagnostics} onBrowseInventory={onBrowseInventory} onOpenNewPage={onOpenNewPage} onSelectWorkItem={onSelectWorkItem} />;
}

function ContentWorkflowIntentStart({
  entry,
  diagnostics,
  onBrowseInventory,
  onOpenNewPage,
  onSelectWorkItem
}: {
  entry: ContentWorkflowEntryResponse;
  diagnostics: ContentDiagnosticsResponse | null;
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
          ) : <ContentWorkflowEmptyRecommendations diagnostics={diagnostics} />}
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-600">
          Dane w tym miejscu służą tylko do odczytu. Wybranie strony nie zmienia treści ani nie publikuje niczego.
        </section>
      </div>
    </main>
  );
}

function ContentWorkflowEmptyRecommendations({ diagnostics }: { diagnostics: ContentDiagnosticsResponse | null }) {
  const decision = diagnostics?.marketer_decision;
  if (decision?.status !== "blocked") {
    return <p className="mt-4 rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-600">Nie ma teraz rekomendacji opartych na wystarczających danych. Możesz wyszukać stronę lub przejrzeć cały serwis.</p>;
  }
  return <section className="mt-4 rounded-2xl border border-wait/30 bg-wait/5 p-5 text-sm text-ink" data-testid="content-workflow-data-blocker">
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-wait">Blokada danych</p>
    <h3 className="mt-2 text-lg font-semibold">{decision.decision}</h3>
    <p className="mt-2 leading-6 text-slate-700">{decision.why_it_matters}</p>
    <p className="mt-3 font-semibold leading-6 text-slate-800">Następny bezpieczny krok: {decision.safe_next_action}</p>
    {decision.source_connector_labels.length ? <p className="mt-3 text-xs leading-5 text-slate-600">Źródła wymagające odczytu: {decision.source_connector_labels.join(", ")}</p> : null}
    {decision.evidence_ids.length ? <p className="mt-2 break-words text-xs leading-5 text-slate-600">Dowody blokady: {decision.evidence_ids.join(", ")}</p> : null}
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
    <dl className="mt-6 grid gap-3 sm:grid-cols-2"><InfoTile label="Cel" value={workspace.brief.purpose} /><InfoTile label="Usługa" value={workspace.brief.service} /><InfoTile label="Odbiorca" value={workspace.brief.audience} /><InfoTile label="Intencja wyszukiwania" value={workspace.brief.search_intent} /><InfoTile label="Miejsce w serwisie" value={workspace.brief.proposed_ia_location} /></dl>
    <section className="mt-7 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-800">Pokrycie istniejących treści</p><h2 className="mt-2 text-xl font-semibold text-ink">{guard.label}</h2><p className="mt-2 text-sm leading-6 text-slate-700">{guard.reason}</p><details className="mt-4 rounded-xl border border-emerald-200 bg-white px-3 py-2"><summary className="cursor-pointer text-sm font-semibold text-ink">Sprawdzone strony i dowody</summary>{guard.candidates.length ? <ul className="mt-3 space-y-3">{guard.candidates.map((candidate) => <li key={`${candidate.url}-${candidate.match_kind}`} className="border-t border-slate-100 pt-3 text-sm first:border-t-0 first:pt-0"><span className="font-semibold text-ink">{candidate.title}</span><span className="mt-1 block text-xs text-slate-600">{candidate.url}</span><span className="mt-2 block text-xs text-slate-700">{overlapMatchLabel(candidate.match_kind)}</span><EvidenceIds evidenceIds={candidate.evidence_ids} /></li>)}</ul> : <p className="mt-3 text-sm leading-6 text-slate-700">{overlapEmptyStateCopy(guard.disposition)}</p>}<EvidenceIds evidenceIds={guard.evidence_ids} label="Dowody sprawdzonego katalogu" /></details><p className="mt-4 text-xs leading-5 text-slate-600">{guard.caveat}</p></section>
    <NewPagePlanningFoundation workspace={workspace} />
  </NewPageShell>;
}

function NewPagePlanningFoundation({ workspace }: { workspace: ContentNewPageBriefWorkspace }) {
  const queryClient = useQueryClient();
  const [serviceCardId, setServiceCardId] = useState("");
  const [confirmedBy, setConfirmedBy] = useState("");
  const foundation = useMutation({
    mutationFn: () => createContentNewPageFoundation(workspace.brief.brief_id, {
      expected_brief_digest: workspace.brief.brief_digest,
      expected_overlap_digest: workspace.overlap_digest,
      service_card_id: serviceCardId,
      confirmed_by: confirmedBy
    }),
    onSuccess: () => queryClient.invalidateQueries({
      queryKey: ["content-workflow", "new-page-brief", workspace.brief.brief_id]
    })
  });
  if (workspace.foundation) {
    return <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Plan nowej strony</h2><p className="mt-2 text-sm leading-6 text-slate-700">{workspace.review_reason}</p><p className="mt-3 text-sm font-semibold text-action">{workspace.next_action_label}</p><p className="mt-2 text-sm leading-6 text-slate-700">Wybrany zatwierdzony kontekst usługi: {workspace.foundation.service_label}. Nowa strona nie ma jeszcze publicznego URL-a, inventory ani danych historycznych.</p><NewPagePlanningProposal briefId={workspace.brief.brief_id} /><NewPageCanonicalDocument briefId={workspace.brief.brief_id} /></section>;
  }
  if (workspace.overlap_guard.disposition !== "no_conflict") {
    return <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Podstawa planowania</h2><p className="mt-2 text-sm leading-6 text-slate-700">{workspace.review_reason}</p><p className="mt-3 text-sm font-semibold text-slate-700">{workspace.next_action_label}</p></section>;
  }
  return <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Podstawa planowania</h2><p className="mt-2 text-sm leading-6 text-slate-700">{workspace.review_reason}</p><div className="mt-4 space-y-3"><p className="text-sm leading-6 text-slate-700">Wybierz świadomie zatwierdzoną kartę usługi. WILQ nie dopasowuje jej automatycznie do opisu briefu.</p>{workspace.service_options.length ? <><label className="block text-sm font-semibold text-ink">Karta usługi<select className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={serviceCardId} onChange={(event) => setServiceCardId(event.target.value)}><option value="">Wybierz kartę</option>{workspace.service_options.map((option) => <option key={option.service_card_id} value={option.service_card_id}>{option.label}</option>)}</select></label><label className="block text-sm font-semibold text-ink">Potwierdza<input className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={confirmedBy} onChange={(event) => setConfirmedBy(event.target.value)} placeholder="Imię i nazwisko" /></label><button type="button" disabled={!serviceCardId || confirmedBy.trim().length < 2 || foundation.isPending} className="rounded-xl bg-action px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50" onClick={() => foundation.mutate()}>{foundation.isPending ? "Zapisuję podstawę…" : "Zapisz podstawę planowania"}</button>{foundation.data ? <p className="text-sm leading-6 text-action">{foundation.data.safe_next_step}</p> : null}{foundation.isError ? <p className="text-sm leading-6 text-wait">Nie udało się zapisać podstawy. Odśwież brief i sprawdź dane ponownie.</p> : null}</> : <p className="text-sm leading-6 text-wait">Nie ma obecnie zatwierdzonej karty usługi. WILQ nie utworzy podstawy planowania bez takiego źródła.</p>}</div></section>;
}

function NewPageCanonicalDocument({ briefId }: { briefId: string }) {
  const queryClient = useQueryClient();
  const document = useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId, "canonical-document"],
    queryFn: () => getContentNewPageCanonicalDocument(briefId),
    staleTime: 15_000
  });
  if (document.isLoading) return <p className="mt-4 text-sm text-slate-600">Sprawdzam stan dokumentu…</p>;
  if (document.error || !document.data) return <p className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm text-ink">Nie udało się odczytać kanonicznego dokumentu. Plan i brief nie zostały przez to zmienione.</p>;
  const refreshDocument = () => {
    void queryClient.invalidateQueries({
      queryKey: ["content-workflow", "new-page-brief", briefId]
    });
  };
  return <>
    <NewPageDocumentState workspace={document.data} />
    <NewPageDocumentCommands briefId={briefId} workspace={document.data} onChanged={refreshDocument} />
    <NewPageDeliveryAction briefId={briefId} workspace={document.data} />
    {document.data.status === "document_approved" && document.data.canonical_revision ? <NewPagePublicDeployment workspace={document.data} onChanged={refreshDocument} /> : null}
  </>;
}

function NewPageDocumentState({ workspace }: { workspace: ContentNewPageCanonicalDocumentWorkspace }) {
  const revision = workspace.canonical_revision;
  const materialCount = workspace.assigned_source_material_ids.length;
  const cardCount = workspace.assigned_knowledge_card_ids.length;
  return <section className="mt-5 rounded-2xl border border-sky-200 bg-sky-50/50 p-4" data-testid="new-page-canonical-document"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-action">Kanoniczny dokument</p><h3 className="mt-2 text-lg font-semibold text-ink">{workspace.title}</h3><p className="mt-2 text-sm leading-6 text-slate-700">{workspace.safe_next_step}</p><dl className="mt-4 grid gap-3 sm:grid-cols-2"><InfoTile label="Stan dokumentu" value={documentStatusLabel(workspace.document_status)} /><InfoTile label="Źródło publiczne" value="Nie dotyczy — to nowa strona." /><InfoTile label="Rewizja" value={revision ? `${revision.revision_id} · ${revision.content_digest.slice(0, 12)}…` : "Nie utworzono"} /><InfoTile label="Review" value={workspace.revision_review ? reviewLabel(workspace.revision_review.decision) : "Nie zapisano"} /><InfoTile label="Przypisane materiały" value={materialCount ? `${materialCount} zapisanych materiałów` : "Nie zapisano w rewizji"} /><InfoTile label="Karty wiedzy" value={cardCount ? `${cardCount} zapisanych kart` : "Nie zapisano w rewizji"} /></dl><p className="mt-4 text-xs leading-5 text-slate-600">To nie jest porównanie z obecną stroną ani potwierdzenie publikacji. WILQ nie tworzy tu szkicu WordPressa.</p></section>;
}

function NewPageDocumentCommands({ briefId, workspace, onChanged }: { briefId: string; workspace: ContentNewPageCanonicalDocumentWorkspace; onChanged: () => void }) {
  if (workspace.status === "ready_for_document") {
    return <NewPageInitialDraft briefId={briefId} workspace={workspace} onChanged={onChanged} />;
  }
  if (workspace.status === "document_review_required" && workspace.canonical_revision) {
    return <NewPageRevisionReview briefId={briefId} workspace={workspace} onChanged={onChanged} />;
  }
  return null;
}

function NewPageInitialDraft({ briefId, workspace, onChanged }: { briefId: string; workspace: ContentNewPageCanonicalDocumentWorkspace; onChanged: () => void }) {
  const [requestedBy, setRequestedBy] = useState("");
  const draft = useMutation({
    mutationFn: () => createContentNewPageInitialDraft(briefId, {
      expected_proposal_id: workspace.proposal_id ?? "",
      expected_planning_digest: workspace.planning_digest ?? "",
      expected_planning_input_digest: workspace.planning_input_digest ?? "",
      requested_by: requestedBy
    }),
    onSuccess: onChanged
  });
  const hasExactPlan = Boolean(workspace.proposal_id && workspace.planning_digest && workspace.planning_input_digest);
  return <section className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4" data-testid="new-page-initial-draft">
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-indigo-700">Dokument nowej strony</p>
    <h4 className="mt-2 text-base font-semibold text-ink">Utwórz pierwszą rewizję</h4>
    <p className="mt-1 text-sm leading-6 text-slate-700">WILQ użyje wyłącznie zaakceptowanego planu, przypisanych źródeł i kart wiedzy. Nie przypisze publicznego URL-a ani nie zapisze niczego w WordPressie.</p>
    <label className="mt-3 block text-sm font-semibold text-ink">Zleca<input className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={requestedBy} onChange={(event) => setRequestedBy(event.target.value)} placeholder="Imię i nazwisko" /></label>
    <button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!hasExactPlan || requestedBy.trim().length < 2 || draft.isPending} onClick={() => draft.mutate()}>{draft.isPending ? "Przygotowuję dokument…" : "Przygotuj pierwszą rewizję"}</button>
    {draft.data ? <p className="mt-2 text-sm leading-6 text-action">{draft.data.safe_next_step}</p> : null}
    {draft.isError ? <p className="mt-2 text-sm leading-6 text-wait">Nie udało się przygotować rewizji. Odśwież plan i sprawdź jego exact tożsamość.</p> : null}
  </section>;
}

function NewPageRevisionReview({ briefId, workspace, onChanged }: { briefId: string; workspace: ContentNewPageCanonicalDocumentWorkspace; onChanged: () => void }) {
  const revision = workspace.canonical_revision!;
  const [reviewedBy, setReviewedBy] = useState("");
  const [decision, setDecision] = useState<"approved" | "needs_changes" | "rejected" | "deferred">("approved");
  const [notes, setNotes] = useState("");
  const [checked, setChecked] = useState(false);
  const evidenceIds = [...new Set(revision.sections.flatMap((section) => section.evidence_ids))];
  const review = useMutation({
    mutationFn: () => reviewContentNewPageRevision(briefId, revision.revision_id, {
      expected_revision_digest: revision.content_digest,
      reviewed_by: reviewedBy,
      decision,
      notes,
      checked_items: checked ? ["Sprawdzono dokument względem zatwierdzonego planu i źródeł."] : [],
      evidence_ids: decision === "approved" ? evidenceIds : []
    }),
    onSuccess: onChanged
  });
  const approvalReady = decision !== "approved" || (checked && evidenceIds.length > 0);
  return <section className="mt-4 rounded-xl border border-amber-200 bg-amber-50/50 p-4" data-testid="new-page-revision-review">
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-amber-800">Review dokumentu</p>
    <h4 className="mt-2 text-base font-semibold text-ink">Podejmij decyzję dla exact rewizji</h4>
    <p className="mt-1 text-sm leading-6 text-slate-700">Decyzja dotyczy rewizji {revision.content_digest.slice(0, 12)}… i nie może zatwierdzić późniejszej wersji.</p>
    <div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="text-sm font-semibold text-ink">Reviewer<input className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} placeholder="Imię i nazwisko" /></label><label className="text-sm font-semibold text-ink">Decyzja<select className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={decision} onChange={(event) => setDecision(event.target.value as typeof decision)}><option value="approved">Zatwierdzam</option><option value="needs_changes">Wymaga zmian</option><option value="rejected">Odrzucam</option><option value="deferred">Odkładam</option></select></label></div>
    <label className="mt-3 flex items-start gap-2 text-sm leading-6 text-slate-700"><input type="checkbox" checked={checked} onChange={(event) => setChecked(event.target.checked)} className="mt-1" />Sprawdziłem dokument względem zatwierdzonego planu i przypisanych dowodów.</label>
    <label className="mt-3 block text-sm font-semibold text-ink">Notatka{decision === "approved" ? " (opcjonalna)" : ""}<textarea className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} /></label>
    <button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={reviewedBy.trim().length < 2 || !approvalReady || (decision !== "approved" && !notes.trim()) || review.isPending} onClick={() => review.mutate()}>{review.isPending ? "Zapisuję review…" : "Zapisz decyzję review"}</button>
    {review.isError ? <p className="mt-2 text-sm leading-6 text-wait">Review nie został zapisany. Odśwież dokument — jego dokładna rewizja mogła się zmienić.</p> : null}
  </section>;
}

function NewPageDeliveryAction({ briefId, workspace }: { briefId: string; workspace: ContentNewPageCanonicalDocumentWorkspace }) {
  const [contentType, setContentType] = useState<"page" | "post">("page");
  const [requestedBy, setRequestedBy] = useState("");
  const readiness = useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId, "delivery-readiness"],
    queryFn: () => getContentNewPageDeliveryReadiness(briefId),
    enabled: workspace.status === "document_approved",
    staleTime: 15_000
  });
  const createAction = useMutation({
    mutationFn: (value: ContentNewPageDeliveryReadiness) => createContentNewPageDeliveryAction(briefId, {
      expected_revision_digest: value.revision_digest ?? "",
      expected_authoring_profile_digest: value.authoring_profile_digest ?? "",
      content_type: contentType,
      requested_by: requestedBy
    })
  });
  if (workspace.status !== "document_approved") return null;
  if (readiness.isLoading) return <p className="mt-4 text-sm text-slate-600">Sprawdzam obserwowane capability szkicu na dev…</p>;
  if (readiness.error || !readiness.data) return <p className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm text-ink">Nie udało się odczytać gotowości delivery. Dokument pozostaje zatwierdzony; nic nie zostało zapisane w WordPressie.</p>;
  if (readiness.data.status !== "ready_for_action") return <section className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-4 text-sm leading-6 text-ink" data-testid="new-page-delivery-blocked"><p className="font-semibold">Szkic na dev jest jeszcze zablokowany</p><p className="mt-1">{readiness.data.safe_next_step}</p></section>;
  const types = readiness.data.allowed_content_types;
  const selectedType = types.includes(contentType) ? contentType : types[0] ?? "page";
  return <section className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4" data-testid="new-page-delivery-ready"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-indigo-700">Przygotowanie akcji dev</p><h4 className="mt-2 text-base font-semibold text-ink">Wybierz typ przyszłego szkicu</h4><p className="mt-1 text-sm leading-6 text-slate-700">WILQ odczytał dozwolone typy z profilu authoringu. Ten krok zapisuje wyłącznie lokalny ActionObject — nie tworzy szkicu i nie zapisuje do WordPressa.</p><div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="text-sm font-semibold text-ink">Typ obiektu<select className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={selectedType} onChange={(event) => setContentType(event.target.value as "page" | "post")}>{types.map((type) => <option key={type} value={type}>{type === "page" ? "Strona" : "Wpis"}</option>)}</select></label><label className="text-sm font-semibold text-ink">Przygotowuje<input className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={requestedBy} onChange={(event) => setRequestedBy(event.target.value)} placeholder="Imię i nazwisko" /></label></div><button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={requestedBy.trim().length < 1 || createAction.isPending} onClick={() => createAction.mutate(readiness.data)}>{createAction.isPending ? "Przygotowuję akcję…" : "Przygotuj ActionObject"}</button>{createAction.data ? <div className="mt-3 rounded-xl border border-indigo-200 bg-white p-3 text-sm leading-6 text-slate-700"><p>Akcja jest zapisana lokalnie. Przejdź przez podgląd, review, potwierdzenie i kontrolę gotowości przed jednym szkicem na dev.</p><a className="mt-2 inline-block font-semibold text-action underline-offset-2 hover:underline" href={`/actions/${encodeURIComponent(createAction.data.id)}`}>Otwórz akcję do sprawdzenia</a></div> : null}{createAction.isError ? <p className="mt-2 text-sm leading-6 text-wait">Akcja nie została przygotowana. Odśwież gotowość delivery i sprawdź dokładną rewizję.</p> : null}</section>;
}

function NewPagePublicDeployment({ workspace, onChanged }: { workspace: ContentNewPageCanonicalDocumentWorkspace; onChanged: () => void }) {
  const revision = workspace.canonical_revision!;
  const [observationId, setObservationId] = useState("");
  const [confirmedBy, setConfirmedBy] = useState("");
  const deployment = useQuery({
    queryKey: ["content-workflow", "public-deployment", revision.work_item_id, revision.revision_id],
    queryFn: () => getContentRevisionPublicDeployment(revision.work_item_id, revision.revision_id),
    staleTime: 15_000
  });
  const confirm = useMutation({
    mutationFn: (value: ContentPublicDeploymentReadResponse["publication_observations"][number]) => postContentRevisionPublicDeployment(revision.work_item_id, revision.revision_id, {
      expected_revision_digest: revision.content_digest,
      wordpress_post_id: value.wordpress_post_id,
      publication_evidence_id: value.publication_evidence_id,
      confirmed_by: confirmedBy
    }),
    onSuccess: () => {
      void deployment.refetch();
      onChanged();
    }
  });
  if (deployment.isLoading) return <p className="mt-4 text-sm text-slate-600">Sprawdzam potwierdzenie publicznego wdrożenia…</p>;
  if (deployment.error || !deployment.data) return <p className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm text-ink">Nie udało się odczytać potwierdzenia wdrożenia. WILQ nie zakłada, że dokument jest publiczny.</p>;
  if (deployment.data.deployment) return <><section className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-4" data-testid="new-page-public-deployment"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-800">Potwierdzone wdrożenie publiczne</p><h4 className="mt-2 text-base font-semibold text-ink">WILQ odczytał publiczną stronę</h4><p className="mt-1 break-words text-sm leading-6 text-slate-700">{deployment.data.deployment.public_url}</p><p className="mt-2 text-sm leading-6 text-slate-700">Potwierdzenie wiąże exact rewizję z obserwacją WordPressa. Nie oznacza, że WILQ opublikował tę stronę.</p></section><NewPageMeasurement workspace={workspace} deployment={deployment.data} onChanged={onChanged} /></>;
  const observations = deployment.data.publication_observations;
  const selected = observations.find((item) => item.publication_evidence_id === observationId);
  return <section className="mt-4 rounded-xl border border-sky-200 bg-sky-50/50 p-4" data-testid="new-page-public-deployment-confirmation"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-sky-800">Potwierdzenie wdrożenia publicznego</p><h4 className="mt-2 text-base font-semibold text-ink">Powiąż rewizję z odczytaną stroną</h4><p className="mt-1 text-sm leading-6 text-slate-700">Najpierw strona musi zostać opublikowana poza WILQ. Ten formularz nie publikuje — zapisuje lokalne potwierdzenie wyłącznie dla jednej obserwacji WordPressa.</p>{observations.length === 0 ? <p className="mt-3 rounded-xl border border-wait/30 bg-white p-3 text-sm leading-6 text-slate-700">Nie ma jeszcze bezpiecznej publicznej obserwacji do wyboru. Odśwież inventory WordPressa po zewnętrznym wdrożeniu; nie wpisuj URL-a ręcznie.</p> : <><label className="mt-3 block text-sm font-semibold text-ink">Zaobserwowana strona<select className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={observationId} onChange={(event) => setObservationId(event.target.value)}><option value="">Wybierz publiczną obserwację</option>{observations.map((item) => <option key={item.publication_evidence_id} value={item.publication_evidence_id}>{item.public_url} · obiekt {item.wordpress_post_id}</option>)}</select></label><label className="mt-3 block text-sm font-semibold text-ink">Potwierdza<input className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={confirmedBy} onChange={(event) => setConfirmedBy(event.target.value)} placeholder="Imię i nazwisko" /></label><button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!selected || confirmedBy.trim().length < 2 || confirm.isPending} onClick={() => selected && confirm.mutate(selected)}>{confirm.isPending ? "Zapisuję potwierdzenie…" : "Potwierdź obserwowane wdrożenie"}</button>{confirm.isError ? <p className="mt-2 text-sm leading-6 text-wait">Potwierdzenie nie zostało zapisane. Odśwież exact rewizję i obserwacje WordPressa.</p> : null}</>}</section>;
}

function NewPageMeasurement({ workspace, deployment, onChanged }: { workspace: ContentNewPageCanonicalDocumentWorkspace; deployment: ContentPublicDeploymentReadResponse; onChanged: () => void }) {
  const revision = workspace.canonical_revision!;
  const createWindow = useMutation({
    mutationFn: () => postContentWorkItemMeasurementWindow({ work_item_id: revision.work_item_id, revision_id: revision.revision_id }),
    onSuccess: onChanged
  });
  const recordOutcome = useMutation({
    mutationFn: (measurementWindowId: string) => postContentWorkItemMeasurementOutcome({ work_item_id: revision.work_item_id, measurement_window_id: measurementWindowId }),
    onSuccess: onChanged
  });
  const createLearning = useMutation({
    mutationFn: (measurementWindowId: string) => postContentWorkItemLearningProposal({ work_item_id: revision.work_item_id, measurement_window_id: measurementWindowId }),
    onSuccess: onChanged
  });
  if (!deployment.measurement_window) return <section className="mt-4 rounded-xl border border-sky-200 bg-sky-50/50 p-4" data-testid="new-page-measurement-window"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-sky-800">Pomiar po wdrożeniu</p><h4 className="mt-2 text-base font-semibold text-ink">Utwórz okno obserwacji</h4><p className="mt-1 text-sm leading-6 text-slate-700">Okno będzie związane wyłącznie z potwierdzonym wdrożeniem tej rewizji. Nie ocenia jeszcze wyniku SEO.</p><button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={createWindow.isPending} onClick={() => createWindow.mutate()}>{createWindow.isPending ? "Tworzę okno…" : "Utwórz okno pomiaru"}</button>{createWindow.isError ? <p className="mt-2 text-sm text-wait">Nie udało się utworzyć okna. WILQ nie zastępuje go innym wdrożeniem.</p> : null}</section>;
  const window = deployment.measurement_window;
  if (!deployment.measurement_outcome) return <section className="mt-4 rounded-xl border border-sky-200 bg-sky-50/50 p-4" data-testid="new-page-measurement-outcome"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-sky-800">Okno pomiaru</p><h4 className="mt-2 text-base font-semibold text-ink">Czekaj na wystarczającą obserwację</h4><p className="mt-1 text-sm leading-6 text-slate-700">Najwcześniejsza data oceny: {window.earliest_verdict_date}. WILQ nie wyprowadza wyniku z braku danych.</p>{deployment.outcome_allowed ? <button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={recordOutcome.isPending} onClick={() => recordOutcome.mutate(window.id)}>{recordOutcome.isPending ? "Sprawdzam wynik…" : "Oceń outcome"}</button> : null}{recordOutcome.isError ? <p className="mt-2 text-sm text-wait">Outcome nie został zapisany. Sprawdź dokładne okno i dostępne facts.</p> : null}</section>;
  if (!deployment.learning_proposal) return <section className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4" data-testid="new-page-learning-proposal"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-indigo-800">Wniosek do review</p><h4 className="mt-2 text-base font-semibold text-ink">Przygotuj proposal learning</h4><p className="mt-1 text-sm leading-6 text-slate-700">To propozycja dla człowieka, nie automatyczna zmiana wiedzy, kolejki ani deklaracja sukcesu.</p><button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={createLearning.isPending} onClick={() => createLearning.mutate(window.id)}>{createLearning.isPending ? "Przygotowuję wniosek…" : "Przygotuj wniosek do review"}</button>{createLearning.isError ? <p className="mt-2 text-sm text-wait">Nie udało się przygotować wniosku; WILQ nie dopisuje wiedzy automatycznie.</p> : null}</section>;
  return <section className="mt-4 rounded-xl border border-indigo-200 bg-indigo-50/50 p-4" data-testid="new-page-learning-record"><p className="text-[11px] font-bold uppercase tracking-[0.14em] text-indigo-800">Wniosek gotowy do review</p><h4 className="mt-2 text-base font-semibold text-ink">{deployment.learning_proposal.decision_summary}</h4><p className="mt-1 text-sm leading-6 text-slate-700">{deployment.learning_proposal.proposed_learning}</p><p className="mt-2 text-xs leading-5 text-slate-600">Wymaga akceptacji człowieka; nie aktualizuje wiedzy ani kolejki automatycznie.</p></section>;
}

function documentStatusLabel(status: ContentNewPageCanonicalDocumentWorkspace["document_status"]) {
  return { not_created: "Nie utworzono", unreviewed: "Czeka na review", approved: "Zatwierdzona", needs_changes: "Wymaga zmian", rejected: "Odrzucona", deferred: "Odłożona" }[status];
}

function reviewLabel(decision: NonNullable<ContentNewPageCanonicalDocumentWorkspace["revision_review"]>["decision"]) {
  return { approved: "Zatwierdzone", needs_changes: "Wymaga zmian", rejected: "Odrzucone", deferred: "Odłożone" }[decision];
}

function NewPagePlanningProposal({ briefId }: { briefId: string }) {
  const queryClient = useQueryClient();
  const workspace = useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId, "planning-proposal"],
    queryFn: () => getContentNewPagePlanningProposal(briefId),
    staleTime: 15_000,
    refetchInterval: (query) =>
      query.state.data?.proposal_status?.status === "generating" ? 3_000 : false
  });
  const generate = useMutation({
    mutationFn: (digest: string) => createContentNewPagePlanningProposal(briefId, { expected_planning_input_digest: digest, requested_by: "Wilku" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["content-workflow", "new-page-brief", briefId] })
  });
  if (workspace.isLoading) return <p className="mt-4 text-sm leading-6 text-slate-600">Sprawdzam aktualny plan nowej strony…</p>;
  if (workspace.error || !workspace.data) return <p className="mt-4 rounded-xl border border-wait/30 bg-wait/5 px-3 py-2 text-sm leading-6 text-ink">Nie udało się odczytać planu. Brief i podstawa pozostają zapisane; odśwież widok przed kolejnym krokiem.</p>;
  const readiness = workspace.data.readiness;
  if (readiness.status === "blocked") {
    const blocker = readiness.blockers[0];
    return <div className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm leading-6 text-ink"><p className="font-semibold">{blocker?.label ?? "Plan jest jeszcze zablokowany"}</p><p className="mt-1">{blocker?.reason ?? readiness.safe_next_step}</p><p className="mt-2 text-slate-700">{readiness.safe_next_step}</p></div>;
  }
  const proposal = workspace.data.proposal_status;
  if (proposal?.status === "ready" || proposal?.status === "created" || proposal?.status === "idempotent") return <section className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 text-sm leading-6 text-ink" data-testid="new-page-planning-ready"><p className="font-semibold">Plan jest gotowy do review</p><p className="mt-1">{proposal.safe_next_step}</p><p className="mt-2 text-slate-700">Nie publikuje to strony ani nie tworzy szkicu WordPressa.</p>{proposal.proposal ? <NewPagePlanningReview briefId={briefId} proposal={proposal.proposal} onChanged={() => { void queryClient.invalidateQueries({ queryKey: ["content-workflow", "new-page-brief", briefId] }); }} /> : <p className="mt-3 text-wait">Brakuje exact propozycji planu; odśwież stan przed review.</p>}</section>;
  if (proposal?.status === "generating") return <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm leading-6 text-ink" data-testid="new-page-planning-generating"><p className="font-semibold">Plan jest przygotowywany</p><p className="mt-1">{proposal.safe_next_step}</p><p className="mt-2 text-xs text-slate-600">WILQ sprawdza ten exact plan ponownie co kilka sekund — nie uruchamia drugiej generacji.</p></div>;
  const planningInputDigest = readiness.planning_input_digest;
  if (!planningInputDigest) return <div className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm leading-6 text-ink"><p className="font-semibold">Nie można bezpiecznie zlecić planu</p><p className="mt-1">Brakuje dokładnego identyfikatora wejścia do planu. Odśwież brief przed kolejnym krokiem.</p></div>;
  return <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50/60 p-3 text-sm leading-6 text-ink" data-testid="new-page-planning-ready"><p className="font-semibold">Wejście do planu jest gotowe</p><p className="mt-1">WILQ użyje dokładnego briefu i wybranego kontekstu usługi. Nie przypisuje tej nowej stronie starego URL-a, inventory ani historycznych metryk.</p><button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white" disabled={generate.isPending} onClick={() => generate.mutate(planningInputDigest)}>{generate.isPending ? "Uruchamiam plan…" : "Przygotuj plan"}</button>{generate.isError ? <p className="mt-2 text-wait">Nie udało się zlecić planu. Odśwież stan i spróbuj ponownie.</p> : null}</div>;
}

function NewPagePlanningReview({ briefId, proposal, onChanged }: { briefId: string; proposal: ContentPlanningProposal; onChanged: () => void }) {
  const [reviewedBy, setReviewedBy] = useState("");
  const [decision, setDecision] = useState<"approved" | "needs_changes">("approved");
  const [checked, setChecked] = useState(false);
  const [notes, setNotes] = useState("");
  const review = useMutation({
    mutationFn: () => reviewContentNewPagePlanning(briefId, {
      expected_proposal_id: proposal.proposal_id ?? "",
      expected_planning_digest: proposal.planning_digest,
      expected_planning_input_digest: proposal.planning_input_digest ?? "",
      decision,
      reviewed_by: reviewedBy,
      checked_items: checked ? ["Sprawdzono cel, strukturę, źródła i przypisanie do usługi."] : [],
      notes
    }),
    onSuccess: onChanged
  });
  const exactPlan = Boolean(proposal.proposal_id && proposal.planning_input_digest);
  return <div className="mt-4 border-t border-emerald-200 pt-4" data-testid="new-page-planning-review">
    <h4 className="font-semibold text-ink">Review planu</h4>
    <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">{proposal.sections.map((section) => <li key={section.section_id || section.heading}><span className="font-medium">{section.heading}</span> — {section.purpose}</li>)}</ul>
    <div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="font-semibold text-ink">Reviewer<input className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} placeholder="Imię i nazwisko" /></label><label className="font-semibold text-ink">Decyzja<select className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={decision} onChange={(event) => setDecision(event.target.value as typeof decision)}><option value="approved">Zatwierdzam plan</option><option value="needs_changes">Plan wymaga zmian</option></select></label></div>
    <label className="mt-3 flex items-start gap-2 text-slate-700"><input type="checkbox" checked={checked} onChange={(event) => setChecked(event.target.checked)} className="mt-1" />Sprawdziłem cel, strukturę, źródła i dopasowanie do usługi.</label>
    <label className="mt-3 block font-semibold text-ink">Notatka{decision === "approved" ? " (opcjonalna)" : ""}<textarea className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} /></label>
    <button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 font-semibold text-white disabled:opacity-50" disabled={!exactPlan || reviewedBy.trim().length < 2 || (decision === "approved" && !checked) || (decision === "needs_changes" && !notes.trim()) || review.isPending} onClick={() => review.mutate()}>{review.isPending ? "Zapisuję review…" : "Zapisz review planu"}</button>
    {review.isError ? <p className="mt-2 text-wait">Nie udało się zapisać review. Odśwież plan — jego exact tożsamość mogła się zmienić.</p> : null}
  </div>;
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

function EvidenceIds({ evidenceIds, label = "Dowody" }: { evidenceIds: string[]; label?: string }) {
  return evidenceIds.length ? <p className="mt-2 break-words text-[11px] leading-5 text-slate-500">{label}: {evidenceIds.join(", ")}</p> : <p className="mt-2 text-[11px] leading-5 text-wait">{label}: brak potwierdzonego dowodu</p>;
}

function overlapMatchLabel(kind: ContentNewPageBriefWorkspace["overlap_guard"]["candidates"][number]["match_kind"]) {
  if (kind === "same_title") return "Podstawa dopasowania: ten sam tytuł strony.";
  if (kind === "shared_intent") return "Podstawa dopasowania: wspólna intencja wyszukiwania.";
  return "Podstawa dopasowania: wspólna usługa.";
}

function overlapEmptyStateCopy(disposition: ContentNewPageBriefWorkspace["overlap_guard"]["disposition"]) {
  if (disposition === "no_conflict") return "Nie znaleziono strony z bezpośrednim pokryciem. Poniżej są dowody z katalogu sprawdzonego dla tego briefu.";
  return "Nie ma potwierdzonych danych pozwalających ocenić pokrycie.";
}
