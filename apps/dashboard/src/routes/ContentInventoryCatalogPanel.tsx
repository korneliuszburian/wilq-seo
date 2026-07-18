import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getContentInventoryMaterial, postContentInventoryBinding, type ContentInventoryCatalogResponse, type ContentInventoryMaterialResponse, type ContentServiceProfileResponse, type ContentWorkItemQueueResponse } from "../lib/api";

export function ContentInventoryCatalogPanel({
  catalog,
  queue,
  serviceProfile,
  onSelectWorkItem
}: {
  catalog: ContentInventoryCatalogResponse;
  queue: ContentWorkItemQueueResponse;
  serviceProfile: ContentServiceProfileResponse | null;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [inspectedUrl, setInspectedUrl] = useState<string | null>(null);
  const bind = useMutation({
    mutationFn: postContentInventoryBinding,
    onSuccess: (result) => {
      if (result.status === "ready" && result.work_item_id) onSelectWorkItem(result.work_item_id);
    }
  });
  const material = useQuery({
    queryKey: ["content-workflow", "inventory-material", inspectedUrl],
    queryFn: () => getContentInventoryMaterial(inspectedUrl ?? ""),
    enabled: Boolean(inspectedUrl)
  });
  const candidateByUrl = useMemo(() => {
    const map = new Map<string, string>();
    for (const candidate of queue.candidates) {
      for (const value of [candidate.source_public_url, candidate.final_canonical_url, candidate.intended_final_url]) {
        if (value) map.set(normalizeUrl(value), candidate.work_item_id);
      }
    }
    return map;
  }, [queue.candidates]);
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const items = useMemo(
    () => catalog.items.filter((item) =>
      (showAll || item.material_status !== "url_only") &&
      (!normalizedSearch || `${item.title} ${item.path} ${item.url} ${item.acf_section_headings.join(" ")}`
        .toLocaleLowerCase()
        .includes(normalizedSearch))
    ),
    [catalog.items, normalizedSearch, showAll]
  );

  return (
    <section className="mb-6 rounded-md border border-line bg-white p-4" aria-label="Pełny inventory WordPress">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-normal text-slate-700">Wszystkie strony i sekcje</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            To jest pełny, read-only spis pobrany z WordPressa. Rekomendowane okazje są osobną kolejką — nic nie zostaje wybrane automatycznie.
          </p>
        </div>
        <div className="rounded-md border border-line bg-surface px-3 py-2 text-right">
          <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">Inventory</div>
          <div className="mt-1 text-lg font-semibold text-ink">{catalog.total_count} adresów</div>
          <div className="mt-1 text-xs text-slate-600">{catalog.ready_count} z materiałem · {catalog.blocked_count} tylko URL</div>
            <div className="mt-1 text-xs text-slate-500">
              Sitemap: {catalog.coverage.status === "unknown"
                ? "coverage niepotwierdzone"
                : `${catalog.coverage.returned_count}/${catalog.coverage.source_count ?? catalog.coverage.returned_count}`}
            </div>
            {catalog.coverage.public_sitemap_returned_count !== null && catalog.coverage.public_sitemap_returned_count !== undefined ? (
              <div className="mt-1 text-xs text-slate-500">Publiczna mapa: {catalog.coverage.public_sitemap_returned_count} adresów</div>
            ) : null}
        </div>
      </div>
      {catalog.coverage.caveat ? (
        <p className="mt-3 rounded-md border border-wait/30 bg-wait/10 px-3 py-2 text-xs leading-5 text-slate-700" data-testid="content-inventory-coverage">
          {catalog.coverage.caveat}
        </p>
      ) : null}
      <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="content-inventory-search">
        Szukaj po adresie, tytule lub sekcji
      </label>
      {serviceProfile?.service_sections?.length ? (
        <div className="mt-4 rounded-md border border-line bg-surface p-3">
          <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">Karty usług do dopasowania</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {serviceProfile.service_sections.map((service) => <span key={service.card_id} className="rounded-full border border-line bg-white px-2 py-1 text-xs text-slate-700">{service.title}</span>)}
          </div>
        </div>
      ) : null}
      {inspectedUrl ? <InventoryMaterialPreview material={material.data} isLoading={material.isLoading} url={inspectedUrl} /> : null}
      <input
        id="content-inventory-search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="np. doradztwo, BDO, /oferta/…"
        className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 text-sm outline-none focus:border-action"
      />
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <button type="button" className={`rounded-full border px-3 py-1 font-semibold ${!showAll ? "border-action bg-action/10 text-action" : "border-line bg-white text-slate-600"}`} onClick={() => setShowAll(false)}>
          Gotowe do odczytu ({catalog.ready_count + catalog.partial_count})
        </button>
        <button type="button" className={`rounded-full border px-3 py-1 font-semibold ${showAll ? "border-action bg-action/10 text-action" : "border-line bg-white text-slate-600"}`} onClick={() => setShowAll(true)}>
          Pokaż wszystkie ({catalog.total_count})
        </button>
        {!showAll ? <span className="text-slate-500">Adresy bez materiału są pokazane dopiero po świadomym rozwinięciu.</span> : null}
      </div>
      <div className="mt-4 max-h-[34rem] overflow-auto rounded-md border border-line">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-surface text-xs uppercase tracking-normal text-slate-500">
            <tr><th className="px-3 py-2">Strona</th><th className="px-3 py-2">Typ</th><th className="px-3 py-2">Sygnał</th><th className="px-3 py-2">Sekcje ACF</th><th className="px-3 py-2">Działanie</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {items.map((item) => {
              const workItemId = candidateByUrl.get(normalizeUrl(item.url));
              return (
                <tr key={item.catalog_id} className="align-top">
                  <td className="px-3 py-3"><div className="font-medium text-ink">{item.title || item.path}</div><div className="mt-1 text-xs text-slate-500">{item.path}</div>{item.content_summary ? <div className="mt-1 max-w-xl text-xs leading-5 text-slate-600">{item.content_summary}</div> : null}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.content_type}<div className="mt-1 font-medium text-slate-700">{materialLabel(item.material_status)}</div></td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.metrics_status === "available" ? <><div className="font-medium text-action">GSC/GA4 dostępne</div><div className="mt-1">{item.metrics_impressions.toLocaleString("pl-PL")} wyśw. · {item.metrics_clicks.toLocaleString("pl-PL")} klik.</div><div className="mt-1 text-slate-500">{item.metrics_query_count} zapytań · {item.metrics_evidence_ids.length} evidence</div></> : <span className="text-wait">Brak exact metryk</span>}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.acf_section_count ? item.acf_section_headings.join(" · ") : item.acf_field_names.length ? `${item.acf_field_names.length} pól ACF (bez rozpoznanych nagłówków)` : "Brak wystawionych sekcji ACF"}{item.content_word_count ? <div className="mt-1 text-slate-500">{item.content_word_count} słów treści</div> : null}</td>
                  <td className="px-3 py-3"><div className="flex flex-wrap gap-2">{workItemId ? <button type="button" className="rounded bg-action px-2 py-1 text-xs font-semibold text-white" onClick={() => onSelectWorkItem(workItemId)}>Otwórz plan</button> : <button type="button" className="rounded bg-action px-2 py-1 text-xs font-semibold text-white disabled:opacity-50" disabled={bind.isPending} onClick={() => bind.mutate(item.url)}>{bind.isPending ? "Czytam materiał…" : item.material_status === "url_only" ? "Sprawdź i rozpocznij" : "Rozpocznij workflow"}</button>}<button type="button" className="rounded border border-line bg-white px-2 py-1 text-xs font-semibold text-slate-700" onClick={() => setInspectedUrl(item.url)}>{inspectedUrl === item.url ? "Materiał otwarty" : "Sprawdź materiał"}</button></div>{!workItemId ? <div className="mt-2 text-xs text-slate-500">Binding opiera się na dokładnym URL-u i aktualnym inventory evidence; adresy bez REST/ACF są sprawdzane przez publiczny HTML.</div> : null}{bind.error ? <div className="mt-2 text-xs text-wait">{bind.error.message}</div> : null}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!items.length && <p className="p-4 text-sm text-slate-600">Brak adresów pasujących do wyszukiwania.</p>}
      </div>
    </section>
  );
}

function InventoryMaterialPreview({ material, isLoading, url }: { material: ContentInventoryMaterialResponse | undefined; isLoading: boolean; url: string }) {
  return <section className="mb-4 rounded-md border border-action/30 bg-action/5 p-4" aria-live="polite"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">Materiał źródłowy do decyzji</div><h3 className="mt-1 text-base font-semibold text-ink">{material?.title || url}</h3></div>{material?.status === "ready" ? <div className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-action">{material.source_kind === "wordpress_rest" ? "WordPress REST" : "wyrenderowany the_content"}</div> : null}</div>{isLoading ? <p className="mt-3 text-sm text-slate-600">Czytam aktualny materiał WordPress…</p> : material?.status === "blocked" ? <p className="mt-3 text-sm text-wait">{material.blocker || "Brak materiału do odczytu."}</p> : material ? <><div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-600"><span>{material.content_word_count ?? 0} słów</span><span>{material.section_headings.length} nagłówków</span><span>{material.acf_field_names.length} pól ACF</span><span>{material.material_confidence === "source_bound" ? "źródło bezpośrednie" : "review-required: HTML"}</span>{material.evidence_id ? <span>źródło: {material.evidence_id}</span> : null}</div><div className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded border border-line bg-white p-3 text-sm leading-6 text-slate-700">{material.content_text || "Brak widocznego tekstu."}</div>{material.acf_section_headings.length ? <div className="mt-3 text-xs text-slate-600">ACF: {material.acf_section_headings.join(" · ")}</div> : null}<div className="mt-2 text-xs text-slate-500">Lineage: {material.source_field_lineage.join(" · ")}</div></> : null}</section>;
}

function normalizeUrl(value: string) {
  const raw = value.trim();
  let path = raw;
  try {
    path = new URL(raw).pathname;
  } catch {
    // Keep relative WordPress paths as-is.
  }
  return path.toLocaleLowerCase().replace(/[ąćęłńóśźż]/g, (char) => ({ ą: "a", ć: "c", ę: "e", ł: "l", ń: "n", ó: "o", ś: "s", ź: "z", ż: "z" }[char] ?? char)).replace(/[-_\s]+/g, "-").replace(/\/$/, "") || "/";
}

function materialLabel(status: ContentInventoryCatalogResponse["items"][number]["material_status"]) {
  return {
    content_and_structure: "Treść + struktura",
    content_summary: "Skrót treści",
    structure_only: "Sama struktura",
    url_only: "Sam adres"
  }[status];
}
