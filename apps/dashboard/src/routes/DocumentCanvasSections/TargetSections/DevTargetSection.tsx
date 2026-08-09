import { useEffect, useRef, useState } from "react";

import type {
  ContentTargetDiscovery,
  ContentTargetMappingPreview
} from "../shared";

export function DevTargetLivePreview({ url }: { url: string }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    const trigger = triggerRef.current;
    if (!dialog) return;
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    closeRef.current?.focus();
    return () => {
      if (typeof dialog.close === "function" && dialog.open) {
        dialog.close();
      } else {
        dialog.removeAttribute("open");
      }
      trigger?.focus();
    };
  }, [open]);

  return (
    <>
      <button
        className="mt-3 w-full rounded-md border border-line bg-white px-3 py-2 text-left text-sm font-semibold text-action hover:border-action"
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(true)}
      >
        Otwórz podgląd strony dev
      </button>
      {open ? (
        <dialog
          aria-labelledby="dev-target-live-preview-title"
          className="h-[min(88vh,64rem)] w-[min(96vw,90rem)] rounded-2xl bg-white p-4 shadow-2xl backdrop:bg-slate-950/45 lg:p-5"
          onCancel={(event) => {
            event.preventDefault();
            setOpen(false);
          }}
          ref={dialogRef}
        >
          <section className="flex h-full flex-col">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-ink" id="dev-target-live-preview-title">Podgląd strony dev</h2>
                <p className="mt-1 text-sm leading-6 text-slate-700">
                  To jest bieżąca strona dev jako punkt odniesienia. Nie pokazuje niezapisanych zmian z mapowania i nie zmienia WordPressa.
                </p>
              </div>
              <button
                aria-label="Zamknij podgląd strony dev"
                className="rounded-md border border-line px-3 py-2 text-sm font-semibold text-slate-700 hover:border-action hover:text-action"
                ref={closeRef}
                type="button"
                onClick={() => setOpen(false)}
              >
                Zamknij
              </button>
            </div>
            <div className="mt-3 flex justify-end">
              <a
                className="text-sm font-semibold text-action hover:underline"
                href={url}
                rel="noreferrer"
                target="_blank"
              >
                Otwórz stronę dev w nowej karcie
              </a>
            </div>
            <iframe
              className="mt-3 min-h-0 flex-1 rounded-md border border-line bg-white"
              referrerPolicy="no-referrer"
              sandbox="allow-same-origin"
              src={url}
              title="Referencyjny podgląd strony dev"
            />
          </section>
        </dialog>
      ) : null}
    </>
  );
}

export function ComponentMappingList({
  components
}: {
  components: ContentTargetMappingPreview["components"];
}) {
  if (components.length === 0) {
    return null;
  }
  return (
    <details className="mt-3 rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer font-semibold text-ink">
        Elementy dokumentu ({components.length})
      </summary>
      <ul className="mt-3 space-y-2">
        {components.map((component) => (
          <li key={component.component_id} className="rounded-lg bg-white p-3">
            <p className="font-semibold text-ink">{component.label}</p>
            <p className="mt-1 leading-6 text-slate-700">{component.reason}</p>
          </li>
        ))}
      </ul>
    </details>
  );
}

export function DevTargetDetails({ discovery }: { discovery: ContentTargetDiscovery }) {
  if (discovery.relation_status === "unavailable") return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    {discovery.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
  </>;
  if (discovery.relation_status === "ambiguous") return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    <ul className="mt-3 space-y-2">
      {discovery.candidates.map((candidate) => <li key={candidate.observation_evidence.evidence_id} className="rounded-lg bg-slate-50 p-3">
        <p className="font-semibold text-ink">{candidate.post_type === "post" ? "Artykuł" : "Strona"} · {wordpressStatus(candidate.post_status)}</p>
        <p className="mt-1 break-all leading-6">{candidate.url}</p>
      </li>)}
    </ul>
    {discovery.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
  </>;
  const target = discovery.target;
  const observedRelationships = target?.target_contract.authoring_surface?.layouts.flatMap((layout) =>
    layout.relationships.map((relationship) => ({ layout, relationship }))
  ) ?? [];
  return <>
    <p className="mt-3 font-semibold text-ink">{discovery.label}</p>
    <p className="mt-2 leading-6">{discovery.reason}</p>
    {target ? <div className="mt-3 rounded-lg bg-slate-50 p-3">
      <p className="font-semibold text-ink">Zaobserwowana strona robocza</p>
      <p className="mt-1 break-all leading-6">{target.url}</p>
      <p className="mt-2 leading-6">To {target.post_type === "post" ? "artykuł" : "strona"}. Status na dev: {wordpressStatus(target.post_status)}. {target.target_contract.authoring_surface ? `WILQ odczytał ${authoringSurfaceLabel(target.target_contract.authoring_surface.kind).toLocaleLowerCase("pl-PL")}.` : "Nie rozpoznano układu treści na tym obiekcie."}</p>
    </div> : null}
    {observedRelationships.length > 0 ? <details className="mt-3 rounded-lg bg-slate-50 p-3">
      <summary className="cursor-pointer font-semibold text-ink">Odczytane relacje ACF</summary>
      <p className="mt-2 text-sm leading-6 text-slate-700">To jest odczyt bieżącego układu deva. Nie zmienia kolejności ani relacji automatycznie.</p>
      <div className="mt-3 space-y-3">
        {observedRelationships.map(({ layout, relationship }) => <section key={`${layout.section_index ?? layout.name}-${relationship.field_name}`} className="rounded-md bg-white p-3 text-sm">
          <p className="font-semibold text-ink">{layout.label || layout.name} · {relationship.field_name}</p>
          <p className="mt-1 leading-6 text-slate-700">{relationship.reason}</p>
          {relationship.status === "available" ? <ul className="mt-2 space-y-1 text-slate-700">
            {relationship.items.map((item) => <li key={item.relationship_id}>{item.label}</li>)}
          </ul> : null}
        </section>)}
      </div>
    </details> : null}
    {discovery.caveats.map((caveat) => <p key={caveat} className="mt-2 leading-6 text-slate-600">{caveat}</p>)}
    <details className="mt-3 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
      <summary className="cursor-pointer font-semibold text-slate-700">Szczegóły techniczne odczytu</summary>
      <p className="mt-2">Środowisko: {target?.target_contract.environment ?? "brak"}. Zapis: niedozwolony.</p>
      <p className="mt-2 break-all">Identyfikator obserwacji: {target?.observation_evidence.evidence_id ?? "brak"}</p>
      <p className="mt-2 break-all">Identyfikator kontraktu: {target?.target_contract_digest ?? "brak"}</p>
    </details>
  </>;
}

export function wordpressStatus(status: string) {
  return { publish: "opublikowany", draft: "szkic", pending: "oczekuje na przegląd" }[status] ?? status;
}

export function wordpressObjectLabel(postType: string) {
  return { post: "artykuł", page: "stronę" }[postType] ?? "obiekt";
}

export function authoringSurfaceLabel(kind: "acf_flexible_content" | "wordpress_post_content") {
  return kind === "acf_flexible_content" ? "Układ ACF Flexible Content" : "Treść wpisu WordPress";
}
