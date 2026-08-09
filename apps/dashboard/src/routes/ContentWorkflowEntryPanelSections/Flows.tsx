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

export function ContentWorkflowInventoryBrowse({ inventory, onReturn, onSelectWorkItem }: { inventory: ContentInventoryCatalogResponse | null; onReturn: () => void; onSelectWorkItem: (workItemId: string) => void }) {
  const [filter, setFilter] = useState("");
  const items = useMemo(() => {
    const query = filter.trim().toLocaleLowerCase("pl-PL");
    return (inventory?.items ?? []).filter((item) => !query || `${item.title ?? ""} ${item.path} ${item.url}`.toLocaleLowerCase("pl-PL").includes(query));
  }, [filter, inventory]);
  return <main className="min-h-screen bg-slate-50 px-4 py-5 lg:px-7 lg:py-8" data-testid="content-workflow-inventory"><div className="mx-auto max-w-6xl"><button type="button" className="text-sm font-semibold text-action" onClick={onReturn}>← Wróć do wyboru pracy</button><section className="mt-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-action">Przeglądaj cały serwis</p><h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">Publiczne strony do odświeżenia</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">To jest katalog adresów publicznych. Nie potwierdza typu wpisu, układu WordPressa ani możliwości zapisu.</p><input type="search" value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Szukaj tytułu lub adresu" className="mt-5 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-action focus:bg-white" /></section>{inventory ? <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white"><p className="border-b border-slate-100 px-5 py-3 text-sm text-slate-600">Wyniki: {items.length} z {inventory.total_count} adresów</p><div className="divide-y divide-slate-100">{items.map((item) => <button key={item.catalog_id} type="button" className="flex w-full flex-wrap items-center justify-between gap-3 px-5 py-4 text-left hover:bg-slate-50" onClick={() => onSelectWorkItem(item.work_item_id)}><span><span className="block font-semibold text-ink">{item.title || item.path}</span><span className="mt-1 block text-xs text-slate-500">{item.url}</span></span><span className="text-sm font-semibold text-action">Otwórz stronę →</span></button>)}{!items.length ? <p className="px-5 py-6 text-sm text-slate-600">Nie znaleziono pasujących stron.</p> : null}</div></section> : <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">Wczytuję katalog stron…</section>}</div></main>;
}
