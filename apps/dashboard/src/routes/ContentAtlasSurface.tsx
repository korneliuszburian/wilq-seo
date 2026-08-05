import { useMemo, useState } from "react";

import type {
  ContentDocumentWorkspace,
  ContentInventoryCatalogResponse,
  ContentTargetDiscovery
} from "../lib/api";
import { useContentTargetDiscovery } from "./contentWorkflowQueries";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";

type AtlasSection = {
  id: string;
  heading: string;
  kind: "source" | "revision";
};

export function ContentAtlasSurface({
  workspace,
  inventory,
  onReturnToText
}: {
  workspace: ContentDocumentWorkspace;
  inventory: ContentInventoryCatalogResponse | null;
  onReturnToText: () => void;
}) {
  const discovery = useContentTargetDiscovery(workspace.work_item_id, true);
  const sections = useMemo(() => atlasSections(workspace), [workspace]);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(sections[0]?.id ?? null);
  const selectedSection = sections.find((section) => section.id === selectedSectionId) ?? sections[0] ?? null;
  const revision = workspace.canonical_document.revision ?? null;
  const linkedPages = useMemo(
    () => resolveInternalLinks(revision?.internal_links ?? [], inventory),
    [inventory, revision?.internal_links]
  );

  return (
    <main className="mx-auto max-w-[110rem] px-4 py-5 lg:px-8" data-testid="content-atlas">
      <ContentWorkflowWorkspaceHeader />
      <header className="mt-4 flex flex-col justify-between gap-4 rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:flex-row lg:items-start lg:p-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Atlas strony · tylko odczyt</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
            {workspace.source_snapshot.title ?? revision?.title ?? "Wybrana strona"}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
            Tu sprawdzasz, z czego składa się jedna strona: aktualny materiał, dokładna rewizja WILQ,
            potwierdzone linki wewnętrzne i obserwowany podgląd dev. Nie przypisujemy automatycznie pól ACF.
          </p>
        </div>
        <button
          type="button"
          className="shrink-0 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink hover:border-action hover:text-action"
          onClick={onReturnToText}
        >
          Wróć do dokumentu
        </button>
      </header>

      <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(19rem,0.8fr)_minmax(28rem,1.2fr)_minmax(26rem,1fr)]">
        <aside className="rounded-2xl border border-line bg-white p-4 shadow-sm" aria-label="Materiały strony">
          <AtlasPageNode
            label="Obecna strona"
            title={workspace.source_snapshot.title ?? "Nie udało się odczytać tytułu"}
            detail={workspace.source_snapshot.url ?? "Brak publicznego adresu w snapshotcie"}
            tone="source"
          />
          <div className="mx-auto h-6 w-px bg-line" aria-hidden="true" />
          <AtlasPageNode
            label="Rewizja WILQ"
            title={revision?.title ?? workspace.canonical_document.label}
            detail={revision ? "Immutable draft · niepublikowany" : workspace.canonical_document.reason}
            tone="revision"
          />

          <div className="mt-5 border-t border-line pt-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-ink">Sekcje rewizji</h2>
              <span className="rounded-full bg-surface px-2 py-1 text-xs font-semibold text-slate-700">{sections.length}</span>
            </div>
            {sections.length ? (
              <ol className="mt-3 space-y-1">
                {sections.map((section, index) => (
                  <li key={section.id}>
                    <button
                      type="button"
                      className={`flex w-full items-start gap-3 rounded-lg border px-3 py-2 text-left text-sm transition ${
                        selectedSection?.id === section.id
                          ? "border-action bg-action/5 text-action"
                          : "border-transparent text-slate-700 hover:border-line hover:bg-surface"
                      }`}
                      onClick={() => setSelectedSectionId(section.id)}
                    >
                      <span className="mt-0.5 text-xs font-semibold tabular-nums text-slate-500">{String(index + 1).padStart(2, "0")}</span>
                      <span className="font-medium">{section.heading}</span>
                    </button>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="mt-3 text-sm leading-6 text-slate-700">Nie ma zapisanych sekcji exact rewizji.</p>
            )}
          </div>
        </aside>

        <section className="rounded-2xl border border-line bg-white p-4 shadow-sm lg:p-5" aria-label="Potwierdzone połączenia">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Co jest połączone</p>
              <h2 className="mt-1 text-lg font-semibold text-ink">
                {selectedSection ? selectedSection.heading : "Wybierz sekcję"}
              </h2>
            </div>
            <span className="rounded-full border border-line bg-surface px-2 py-1 text-xs font-semibold text-slate-700">
              {selectedSection?.kind === "revision" ? "sekcja rewizji" : "sekcja źródłowa"}
            </span>
          </div>

          <div className="mt-5 grid gap-3">
            <AtlasFact
              label="Aktualna strona"
              value={workspace.source_snapshot.status === "available" ? "odczytana" : workspace.source_snapshot.status}
              detail={workspace.source_snapshot.reason}
            />
            <AtlasFact
              label="Rewizja WILQ"
              value={revision ? "dokładna rewizja istnieje" : "brak rewizji"}
              detail={workspace.canonical_document.reason}
            />
            <AtlasFact
              label="ACF na dev"
              value={acfStatus(discovery.data)}
              detail={acfDetail(discovery.data)}
            />
          </div>

          <div className="mt-5 border-t border-line pt-4">
            <h3 className="text-sm font-semibold text-ink">Potwierdzone linki wewnętrzne rewizji</h3>
            <p className="mt-1 text-sm leading-5 text-slate-700">
              Pokazujemy wyłącznie linki zapisane przy tej exact rewizji — nie „podobne tematy” wywnioskowane przez model.
            </p>
            {linkedPages.length ? (
              <ul className="mt-3 space-y-2">
                {linkedPages.map((link) => (
                  <li key={link.linkId} className="rounded-lg border border-line bg-surface p-3">
                    <p className="font-medium text-ink">{link.title}</p>
                    <p className="mt-1 text-xs text-slate-600">Anchor: {link.anchorText}</p>
                    <a className="mt-1 block break-all text-xs font-medium text-action hover:underline" href={link.url} target="_blank" rel="noreferrer">
                      {link.url}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 rounded-lg bg-surface p-3 text-sm leading-5 text-slate-700">
                Ta rewizja nie ma zapisanych linków wewnętrznych do pokazania w atlasie.
              </p>
            )}
          </div>
        </section>

        <section className="overflow-hidden rounded-2xl border border-line bg-white shadow-sm" aria-label="Podgląd strony dev">
          <div className="flex items-start justify-between gap-3 border-b border-line p-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Podgląd targetu</p>
              <h2 className="mt-1 text-lg font-semibold text-ink">Dev / obserwacja</h2>
            </div>
            <span className="rounded-full bg-surface px-2 py-1 text-xs font-semibold text-slate-700">bez zapisu</span>
          </div>
          <DevPreview discovery={discovery.data ?? null} loading={discovery.isLoading} />
        </section>
      </section>

      <p className="mt-4 rounded-xl border border-line bg-surface px-4 py-3 text-sm leading-6 text-slate-700">
        Następny etap: po potwierdzonym discovery authoring surface dodamy ręczne mapowanie sekcji rewizji do pól ACF.
        Ten widok nie zmienia WordPressa ani targetu dev.
      </p>
    </main>
  );
}

function AtlasPageNode({
  label,
  title,
  detail,
  tone
}: {
  label: string;
  title: string;
  detail: string;
  tone: "source" | "revision";
}) {
  return (
    <section className={`rounded-xl border p-4 ${tone === "revision" ? "border-action/30 bg-action/5" : "border-line bg-surface"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="mt-2 font-semibold leading-5 text-ink">{title}</p>
      <p className="mt-2 break-words text-xs leading-5 text-slate-700">{detail}</p>
    </section>
  );
}

function AtlasFact({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <section className="rounded-xl border border-line p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">{label}</p>
      <p className="mt-1 font-medium text-ink">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-700">{detail}</p>
    </section>
  );
}

function DevPreview({ discovery, loading }: { discovery: ContentTargetDiscovery | null; loading: boolean }) {
  if (loading) return <p className="p-4 text-sm text-slate-700">Odczytuję obserwowany target dev…</p>;
  const target = discovery?.target ?? null;
  if (!target) {
    return (
      <div className="p-4">
        <p className="font-medium text-ink">Nie ma potwierdzonego targetu dev.</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">{discovery?.reason ?? "WILQ nie otrzymał obserwacji targetu dla tej strony."}</p>
      </div>
    );
  }
  return (
    <div>
      <div className="border-b border-line p-4">
        <a className="break-all text-sm font-medium text-action hover:underline" href={target.url} target="_blank" rel="noreferrer">
          Otwórz dev w nowej karcie
        </a>
        <p className="mt-2 text-xs leading-5 text-slate-700">
          Odczyt obserwacji: {target.post_type} · {target.post_status}. Podgląd może być zablokowany przez nagłówki strony.
        </p>
      </div>
      <iframe
        className="h-[38rem] w-full bg-surface"
        title="Podgląd strony na dev"
        src={target.url}
        sandbox="allow-same-origin allow-scripts allow-popups"
      />
    </div>
  );
}

function atlasSections(workspace: ContentDocumentWorkspace): AtlasSection[] {
  const revisionSections = workspace.canonical_document.preview?.sections ?? [];
  if (revisionSections.length) {
    return revisionSections.map((section, index) => ({
      id: section.section_id ?? `revision-${index}`,
      heading: section.heading,
      kind: "revision"
    }));
  }
  return workspace.source_snapshot.ordered_sections.map((section, index) => ({
    id: `source-${index}`,
    heading: section.heading,
    kind: "source"
  }));
}

function acfStatus(discovery: ContentTargetDiscovery | undefined) {
  const surface = discovery?.target?.target_contract.authoring_surface ?? null;
  return surface ? "odczytano surface ACF — bez mapowania" : "nieodczytane / niepotwierdzone";
}

function acfDetail(discovery: ContentTargetDiscovery | undefined) {
  const surface = discovery?.target?.target_contract.authoring_surface ?? null;
  if (!surface) return discovery?.reason ?? "Nie przypisujemy sekcji do ACF bez potwierdzonego authoring surface.";
  return `Root field: ${surface.root_field}. Przypisanie sekcji nadal wymaga decyzji człowieka.`;
}

function resolveInternalLinks(
  links: Array<{ link_id: string; target_url: string; anchor_text: string }>,
  inventory: ContentInventoryCatalogResponse | null
) {
  return links.map((link) => {
    const match = inventory?.items.find((item) => samePublicPath(item.url, link.target_url));
    return {
      linkId: link.link_id,
      url: link.target_url,
      anchorText: link.anchor_text,
      title: match?.title ?? link.anchor_text
    };
  });
}

function samePublicPath(first: string, second: string) {
  try {
    const firstUrl = new URL(first);
    const secondUrl = new URL(second);
    return firstUrl.pathname.replace(/\/$/, "") === secondUrl.pathname.replace(/\/$/, "");
  } catch {
    return false;
  }
}
