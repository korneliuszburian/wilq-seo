import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getContentInventoryMaterial, postContentInventoryBinding, type ContentInventoryCatalogResponse, type ContentInventoryMaterialResponse, type ContentServiceProfileResponse, type ContentWorkItemQueueResponse } from "../lib/api";

type InventoryCatalogView = "ready" | "metrics" | "all";

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
  const [catalogView, setCatalogView] = useState<InventoryCatalogView>("ready");
  const [inspectedUrl, setInspectedUrl] = useState<string | null>(null);
  const [pendingUrl, setPendingUrl] = useState<string | null>(null);
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
  const pendingItem = pendingUrl
    ? catalog.items.find((item) => normalizeUrl(item.url) === normalizeUrl(pendingUrl)) ?? null
    : null;
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
    () => catalog.items
      .filter((item) =>
        matchesInventoryView(item, catalogView) &&
        (!normalizedSearch || `${item.title} ${item.path} ${item.url} ${item.acf_section_headings.join(" ")}`
          .toLocaleLowerCase()
          .includes(normalizedSearch))
      )
      .sort((left, right) => compareInventoryItems(left, right, candidateByUrl)),
    [catalog.items, candidateByUrl, catalogView, normalizedSearch]
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
          <div className="text-[11px] font-semibold uppercase tracking-normal text-slate-500">Zakres stron</div>
          <div className="mt-1 text-lg font-semibold text-ink">{catalog.total_count} adresów</div>
          <div className="mt-1 text-xs text-slate-600">{catalog.ready_count} z materiałem · {catalog.blocked_count} tylko URL</div>
            <div className="mt-1 text-xs text-slate-500">
              Sitemap: {catalog.coverage.status === "unknown"
                ? "coverage niepotwierdzone"
                : `${catalog.coverage.returned_count}/${catalog.coverage.source_count ?? catalog.coverage.returned_count}`}
            </div>
            {catalog.coverage.public_sitemap_returned_count !== null && catalog.coverage.public_sitemap_returned_count !== undefined ? (
              <div className="mt-1 text-xs text-slate-500">
                Publiczna mapa: {catalog.coverage.public_sitemap_returned_count}
                {catalog.coverage.public_sitemap_source_count !== null && catalog.coverage.public_sitemap_source_count !== undefined
                  ? `/${catalog.coverage.public_sitemap_source_count}`
                  : ""} adresów
                {catalog.coverage.public_sitemap_truncated ? " · niepełna" : ""}
              </div>
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
      {pendingItem ? (
        <InventoryWorkflowStartingPanel
          item={pendingItem}
          isPending={bind.isPending}
          error={bind.error?.message ?? bind.data?.blocker ?? null}
        />
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
        <button type="button" className={`rounded-full border px-3 py-1 font-semibold ${catalogView === "ready" ? "border-action bg-action/10 text-action" : "border-line bg-white text-slate-600"}`} onClick={() => setCatalogView("ready")}>
          Do pracy teraz ({catalog.ready_count + catalog.partial_count})
        </button>
        <button type="button" className={`rounded-full border px-3 py-1 font-semibold ${catalogView === "metrics" ? "border-action bg-action/10 text-action" : "border-line bg-white text-slate-600"}`} onClick={() => setCatalogView("metrics")}>
          Z metrykami ({catalog.items.filter((item) => item.metrics_status === "available").length})
        </button>
        <button type="button" className={`rounded-full border px-3 py-1 font-semibold ${catalogView === "all" ? "border-action bg-action/10 text-action" : "border-line bg-white text-slate-600"}`} onClick={() => setCatalogView("all")}>
          Pokaż wszystkie ({catalog.total_count})
        </button>
        {catalogView === "ready" ? <span className="text-slate-500">Najpierw pokazujemy strony z materiałem gotowym do planu.</span> : catalogView === "metrics" ? <span className="text-slate-500">Pokazujemy także adresy URL-only, jeśli mają realne metryki do decyzji.</span> : null}
      </div>
      <div className="mt-4 max-h-[34rem] overflow-auto rounded-md border border-line">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-surface text-xs uppercase tracking-normal text-slate-500">
            <tr><th className="px-3 py-2">Strona</th><th className="px-3 py-2">Typ</th><th className="px-3 py-2">Metryki</th><th className="px-3 py-2">Treść i sekcje</th><th className="px-3 py-2">Działanie</th></tr>
          </thead>
          <tbody className="divide-y divide-line">
            {items.map((item) => {
              const workItemId = candidateByUrl.get(normalizeUrl(item.url));
              return (
                <tr key={item.catalog_id} className="align-top">
                  <td className="px-3 py-3"><div className="font-medium text-ink">{item.title || item.path}</div><div className="mt-1 text-xs text-slate-500">{item.path}</div>{item.content_summary ? <div className="mt-1 max-w-xl text-xs leading-5 text-slate-600">{item.content_summary}</div> : null}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{item.content_type}<div className="mt-1 font-medium text-slate-700">{materialLabel(item.material_status)}</div></td>
              <td className="px-3 py-3 text-xs text-slate-600">{item.metrics_status === "available" ? <><div className="font-medium text-action">GSC/GA4 dostępne</div><div className="mt-1">{item.metrics_impressions.toLocaleString("pl-PL")} wyśw. · {item.metrics_clicks.toLocaleString("pl-PL")} klik.</div><div className="mt-1 text-slate-500">{item.metrics_query_count} zapytań · {item.metrics_evidence_ids.length} źródeł</div></> : <span className="text-wait">Brak dokładnych metryk</span>}</td>
                  <td className="px-3 py-3 text-xs text-slate-600">{inventoryStructureLabel(item)}{item.content_word_count ? <div className="mt-1 text-slate-500">{item.content_word_count} słów treści</div> : null}</td>
              <td className="px-3 py-3"><div className="flex flex-wrap gap-2">{workItemId ? <button type="button" className="rounded bg-action px-2 py-1 text-xs font-semibold text-white" onClick={() => onSelectWorkItem(workItemId)}>Otwórz plan</button> : <button type="button" className="rounded bg-action px-2 py-1 text-xs font-semibold text-white disabled:opacity-50" disabled={bind.isPending && bind.variables === item.url} onClick={() => { setPendingUrl(item.url); setInspectedUrl(item.url); bind.mutate(item.url); }}>{bind.isPending && bind.variables === item.url ? "Czytam materiał…" : item.material_status === "url_only" ? "Sprawdź i rozpocznij" : "Rozpocznij workflow"}</button>}<button type="button" className="rounded border border-line bg-white px-2 py-1 text-xs font-semibold text-slate-700" onClick={() => setInspectedUrl(item.url)}>{inspectedUrl === item.url ? "Materiał otwarty" : "Sprawdź materiał"}</button></div>{!workItemId ? <div className="mt-2 text-xs text-slate-500">Powiązanie opiera się na dokładnym URL-u i aktualnym odczycie strony; adresy bez REST/ACF są sprawdzane przez publiczny HTML.</div> : null}{bind.error ? <div className="mt-2 text-xs text-wait">{bind.error.message}</div> : null}</td>
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

export function InventoryWorkflowStartingPanel({
  item,
  isPending,
  error
}: {
  item: ContentInventoryCatalogResponse["items"][number];
  isPending: boolean;
  error: string | null;
}) {
  return (
    <section className="mb-4 rounded-md border border-action/30 bg-action/5 p-4" aria-live="polite" data-testid="content-inventory-workflow-starting">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-normal text-action">Wybrana strona</div>
          <h3 className="mt-1 text-base font-semibold text-ink">{item.title || item.path}</h3>
          <p className="mt-1 break-all text-xs text-slate-600">{item.url}</p>
        </div>
        <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-action">
          {error ? "Wymaga sprawdzenia" : isPending ? "Przygotowuję workflow" : "Odczyt zakończony"}
        </span>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-700 sm:grid-cols-3">
        <div className="rounded border border-line bg-white px-3 py-2"><span className="font-semibold">Materiał:</span> {materialLabel(item.material_status)}</div>
        <div className="rounded border border-line bg-white px-3 py-2"><span className="font-semibold">Metryki:</span> {item.metrics_status === "available" ? `${item.metrics_impressions.toLocaleString("pl-PL")} wyświetleń · ${item.metrics_clicks.toLocaleString("pl-PL")} kliknięć` : "sprawdzamy exact dane"}</div>
        <div className="rounded border border-line bg-white px-3 py-2"><span className="font-semibold">Następny krok:</span> {error ? "Sprawdź blocker i wybierz inną stronę." : "Dopasujemy usługę, źródła i plan."}</div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">
        {error ?? "Strona jest już wybrana. WILQ ładuje materiał i dopasowane dane; katalog pozostaje dostępny."}
      </p>
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

export function compareInventoryItems(
  left: ContentInventoryCatalogResponse["items"][number],
  right: ContentInventoryCatalogResponse["items"][number],
  candidateByUrl: Map<string, string>
) {
  const leftCandidate = candidateByUrl.has(normalizeUrl(left.url)) ? 0 : 1;
  const rightCandidate = candidateByUrl.has(normalizeUrl(right.url)) ? 0 : 1;
  if (leftCandidate !== rightCandidate) return leftCandidate - rightCandidate;

  const materialRank = {
    content_and_structure: 0,
    content_summary: 1,
    structure_only: 2,
    url_only: 3
  } as const;
  const leftMaterial = materialRank[left.material_status];
  const rightMaterial = materialRank[right.material_status];
  if (leftMaterial !== rightMaterial) return leftMaterial - rightMaterial;

  const leftMetrics = left.metrics_status === "available" ? 0 : 1;
  const rightMetrics = right.metrics_status === "available" ? 0 : 1;
  if (leftMetrics !== rightMetrics) return leftMetrics - rightMetrics;
  if (left.metrics_impressions !== right.metrics_impressions) {
    return right.metrics_impressions - left.metrics_impressions;
  }
  if (left.metrics_clicks !== right.metrics_clicks) return right.metrics_clicks - left.metrics_clicks;
  return `${left.title ?? ""} ${left.path}`.localeCompare(`${right.title ?? ""} ${right.path}`, "pl");
}

export function matchesInventoryView(
  item: ContentInventoryCatalogResponse["items"][number],
  view: InventoryCatalogView
) {
  if (view === "all") return true;
  if (view === "metrics") return item.metrics_status === "available";
  return item.material_status !== "url_only";
}

function materialLabel(status: ContentInventoryCatalogResponse["items"][number]["material_status"]) {
  return {
    content_and_structure: "Treść + struktura",
    content_summary: "Skrót treści",
    structure_only: "Sama struktura",
    url_only: "Sam adres"
  }[status];
}

export function inventoryStructureLabel(item: ContentInventoryCatalogResponse["items"][number]) {
  if (item.acf_section_count) {
    return item.acf_section_headings.length
      ? `ACF: ${item.acf_section_headings.join(" · ")}`
      : `${item.acf_section_count} sekcji ACF`;
  }
  if (item.section_count) {
    return `${item.section_count} nagłówków w treści strony`;
  }
  if (item.acf_field_names.length) {
    return `${item.acf_field_names.length} pól ACF (bez rozpoznanych nagłówków)`;
  }
  return "Brak rozpoznanej struktury";
}
