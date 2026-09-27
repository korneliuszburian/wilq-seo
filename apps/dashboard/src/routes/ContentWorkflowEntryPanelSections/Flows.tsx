import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  createContentNewPageFoundation,
  type ContentInventoryCatalogResponse,
  type ContentNewPageBriefWorkspace
} from "../../lib/api";
import { ContentNewPageTextPreparation } from "../ContentNewPageTextPreparation";
import { NewPageCanonicalDocument, useNewPageCanonicalDocument } from "./CanonicalDocument";

export function NewPageTextFoundation({ workspace }: { workspace: ContentNewPageBriefWorkspace }) {
  const queryClient = useQueryClient();
  const [serviceCardId, setServiceCardId] = useState("");
  const [prepareTextAfterSource, setPrepareTextAfterSource] = useState(false);
  const canonicalDocument = useNewPageCanonicalDocument(
    workspace.brief.brief_id,
    Boolean(workspace.foundation)
  );
  const foundation = useMutation({
    mutationFn: () => createContentNewPageFoundation(workspace.brief.brief_id, {
      expected_brief_digest: workspace.brief.brief_digest,
      expected_overlap_digest: workspace.overlap_digest,
      service_card_id: serviceCardId,
      confirmed_by: "wilku"
    }),
    onSuccess: async () => {
      await queryClient.refetchQueries({
        queryKey: ["content-workflow", "new-page-brief", workspace.brief.brief_id]
      });
    },
    onError: () => {
      setPrepareTextAfterSource(false);
    }
  });
  if (workspace.foundation) {
    return <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Tekst nowej strony</h2><p className="mt-2 text-sm leading-6 text-slate-700">Tekst oprze się na wiedzy o usłudze: {workspace.foundation.service_label}. Nowa strona nie ma jeszcze publicznego URL-a, inventory ani danych historycznych.</p><NewPageCanonicalDocument document={canonicalDocument} onChanged={() => { void queryClient.invalidateQueries({ queryKey: ["content-workflow", "new-page-brief", workspace.brief.brief_id] }); }} />{canonicalDocument.data && !canonicalDocument.data.canonical_revision ? <ContentNewPageTextPreparation briefId={workspace.brief.brief_id} autoStart={prepareTextAfterSource} /> : null}</section>;
  }
  if (workspace.overlap_guard.disposition !== "no_conflict") {
    return <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Zakres źródeł do tekstu</h2><p className="mt-2 text-sm leading-6 text-slate-700">{workspace.review_reason}</p><p className="mt-3 text-sm font-semibold text-slate-700">{workspace.next_action_label}</p></section>;
  }
  return <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5"><h2 className="text-lg font-semibold text-ink">Na czym oprzeć tekst?</h2><p className="mt-2 text-sm leading-6 text-slate-700">Wybierz wiedzę o usłudze. WILQ pokazuje tutaj wyłącznie materiał wcześniej sprawdzony przez zespół, a techniczne kontrole wykona w tle.</p><div className="mt-4 space-y-3">{workspace.service_options.length ? <><label className="block text-sm font-semibold text-ink">Źródło wiedzy<select className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={serviceCardId} onChange={(event) => setServiceCardId(event.target.value)}><option value="">Wybierz źródło wiedzy</option>{workspace.service_options.map((option) => <option key={option.service_card_id} value={option.service_card_id}>{option.label}</option>)}</select></label><button type="button" disabled={!serviceCardId || foundation.isPending} className="rounded-xl bg-action px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50" onClick={() => { setPrepareTextAfterSource(true); foundation.mutate(); }}>{foundation.isPending ? "Przygotowuję tekst…" : "Przygotuj tekst na tej podstawie"}</button>{foundation.isError ? <p className="text-sm leading-6 text-wait">Nie udało się przygotować tekstu na tej podstawie. Odśwież brief i spróbuj ponownie.</p> : null}</> : <p className="text-sm leading-6 text-wait">Nie ma jeszcze sprawdzonej wiedzy o usłudze, na której można bezpiecznie oprzeć tekst.</p>}</div></section>;
}

export function ContentWorkflowInventoryBrowse({ inventory, onReturn, onSelectWorkItem, failed = false, onRetry }: { inventory: ContentInventoryCatalogResponse | null; onReturn: () => void; onSelectWorkItem: (workItemId: string) => void; failed?: boolean; onRetry?: () => void }) {
  const [filter, setFilter] = useState("");
  const inventoryCoverageIsIncomplete = inventory !== null && inventory.coverage.status !== "complete";
  const journalReconciliation = inventory?.journal_reconciliation;
  const journalReadiness = inventory?.journal_readiness;
  const journalRows = journalReadiness?.rows ?? [];
  const evidenceSummary = journalReadiness?.content_evidence_readiness;
  const journalRowsAreComplete = journalReadiness !== undefined
    && journalReadiness !== null
    && journalReadiness.journal_record_count > 0
    && journalReadiness.rows.length === journalReadiness.journal_record_count;
  const journalCurrentObservationCount = journalRows.filter(
    (row) => row.current_catalog_state === "exact_path_observed"
  ).length;
  const journalMissingObservationCount = journalRows.filter(
    (row) => row.current_catalog_state === "not_observed"
  ).length;
  const journalAmbiguousObservationCount = journalRows.filter(
    (row) => row.current_catalog_state === "ambiguous"
  ).length;
  const identityBlockerCount = journalRows.filter(
    (row) => row.content_evidence_readiness.identity.status !== "exact_current"
  ).length;
  const cardBlockerCount = journalRows.filter(
    (row) => row.content_evidence_readiness.service_card.status !== "approved_current"
  ).length;
  const promotionBlockerCount = journalRows.filter(
    (row) => row.content_evidence_readiness.promotion.status !== "approved_current"
  ).length;
  const journalReadinessByPath = useMemo(
    () => new Map(
      journalRows.map((row) => [normalizeInventoryPath(row.canonical_path), row] as const)
    ),
    [journalRows]
  );
  const items = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase("pl-PL");
    return (inventory?.items ?? []).filter((item) => !query || `${item.title ?? ""} ${item.path} ${item.url}`.toLocaleLowerCase("pl-PL").includes(query));
  }, [filter, inventory]);
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-inventory">
      <div className="mx-auto max-w-6xl">
        <button type="button" className="text-sm font-semibold text-action" onClick={onReturn}>← Wróć do wyboru pracy</button>
        <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5">
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-action">{inventoryCoverageIsIncomplete ? "Zakres katalogu nie jest pełny" : "Przeglądaj cały serwis"}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{inventoryCoverageIsIncomplete ? "Wykryte publiczne strony do odświeżenia" : "Publiczne strony do odświeżenia"}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">To jest katalog adresów publicznych. Nie potwierdza typu wpisu, układu WordPressa ani możliwości zapisu.</p>
          {inventoryCoverageIsIncomplete ? <p className="mt-3 max-w-3xl rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-950" data-testid="content-workflow-inventory-coverage-warning">{inventory.coverage.caveat}</p> : null}
          {journalReconciliation && journalReconciliation.status !== "complete" ? <div className="mt-3 max-w-3xl rounded-xl border border-risk/20 bg-red-50 px-3 py-3 text-sm leading-6 text-risk" data-testid="content-workflow-inventory-journal-reconciliation" role="status">Zgodność journalu i inventory: {journalReconciliation.matched_catalog_count} z {journalReconciliation.journal_record_count} URL-i ma exact typed inventory. {journalReconciliation.missing_inventory_binding_count} bez exact inventory binding. {journalReconciliation.matched_authoring_source_count} URL-i ma bezpieczny odczyt authoring; nie potwierdza on finalnego canonical ani bindingu. {journalReconciliation.caveat} {journalReconciliation.safe_next_step}</div> : null}
          {journalReadiness && journalReadiness.status !== "complete" ? <div className="content-evidence-readiness" data-state={journalReadiness.status} data-testid="content-workflow-inventory-journal-readiness" role="status">
            {journalRowsAreComplete && evidenceSummary ? <>
              <p className="content-evidence-readiness__title">Gotowość dowodowa: {evidenceSummary.total_count} URL-i</p>
              <p className="content-evidence-readiness__meta">{journalCurrentObservationCount} ma bieżącą exact obserwację, {journalMissingObservationCount} bez bieżącej exact obserwacji, {journalAmbiguousObservationCount} niejednoznaczna.</p>
              <p className="content-evidence-readiness__meta">Receipt current: {evidenceSummary.authoring_receipt_current_count}; obserwacja do researchu: {evidenceSummary.acquisition_ready_count}; research do review: {evidenceSummary.research_ready_count}.</p>
              <p className="content-evidence-readiness__meta">Blokady — identity: {identityBlockerCount}; karta: {cardBlockerCount}; promocja: {promotionBlockerCount}.</p>
              <p className="content-evidence-readiness__next-step">{journalReadiness.caveat} {journalReadiness.safe_next_step}</p>
            </> : <>Journal zgłasza {journalReadiness.journal_record_count} URL-i, ale przekazał tylko {journalReadiness.rows.length} z {journalReadiness.journal_record_count} oczekiwanych rekordów. Stan jest niekompletny; nie używaj liczników obserwacji do decyzji. {journalReadiness.caveat} {journalReadiness.safe_next_step}</>}
          </div> : null}
          <input type="search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Szukaj tytułu lub adresu" className="mt-5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-action focus:bg-white" />
        </section>
        {inventory ? <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <p className="border-b border-slate-100 px-5 py-3 text-sm text-slate-600">Wyniki: {items.length} z {inventory.total_count} {inventoryCoverageIsIncomplete ? "wykrytych adresów" : "adresów"}</p>
          <div className="divide-y divide-slate-100">
            {items.map((item) => {
              const row = journalReadinessByPath.get(normalizeInventoryPath(item.path));
              const rowReadiness = row?.content_evidence_readiness;
              return (
                <div key={item.catalog_id} className="content-evidence-row">
                  <button type="button" className="flex w-full flex-wrap items-center justify-between gap-3 text-left hover:bg-slate-50" onClick={() => onSelectWorkItem(item.work_item_id)}>
                    <span>
                      <span className="block font-semibold text-ink">{item.title || item.path}</span>
                      <span className="mt-1 block text-xs text-slate-500">{item.url}</span>
                      {rowReadiness ? <span className="content-evidence-row__badge" data-state={rowReadiness.status}>{rowReadiness.status_label}</span> : null}
                    </span>
                    <span className="text-sm font-semibold text-action">Otwórz stronę →</span>
                  </button>
                  {rowReadiness ? <details className="content-evidence-row__details">
                    <summary className="content-evidence-row__summary">Pokaż blocker i źródła</summary>
                    <div className="content-evidence-row__meta">
                      <p>{rowReadiness.safe_next_step}</p>
                      {rowReadiness.blockers.length ? <ul className="content-evidence-row__blockers">{rowReadiness.blockers.slice(0, 3).map((blocker) => <li key={blocker.code}>{blocker.reason}</li>)}</ul> : null}
                      <p className="content-evidence-row__technical">Receipt: {rowReadiness.authoring_inventory_receipt.receipt_id ?? "brak"} · evidence: {rowReadiness.authoring_inventory_receipt.evidence_id ?? "brak"}</p>
                      <p className="content-evidence-row__technical">Acquisition: {rowReadiness.evidence_acquisition.run_id ?? "brak"} · evidence: {rowReadiness.evidence_acquisition.evidence_ids.join(", ") || "brak"}</p>
                      <p className="content-evidence-row__technical">Research: {rowReadiness.research_proposal.proposal_id ?? "brak"} · approved: {rowReadiness.research_proposal.approved ? "tak" : "nie"}</p>
                    </div>
                  </details> : null}
                </div>
              );
            })}
            {!items.length ? <p className="px-5 py-6 text-sm text-slate-600">Nie znaleziono pasujących stron.</p> : null}
          </div>
        </section> : failed ? <section className="mt-4 rounded-2xl border border-wait/30 bg-wait/5 p-5 text-sm leading-6 text-ink" data-testid="content-catalog-failure"><p className="font-semibold">Nie udało się wczytać katalogu stron.</p><p className="mt-1 text-slate-700">Katalog nie został odczytany; nic nie zostało zmienione. Odśwież katalog i spróbuj ponownie.</p>{onRetry ? <button type="button" className="mt-3 rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie wczytać katalog</button> : null}</section> : <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">Wczytuję katalog stron…</section>}
      </div>
    </main>
  );
}

function normalizeInventoryPath(value: string): string {
  const normalized = value.trim().replace(/\/+$/, "");
  return normalized || "/";
}
