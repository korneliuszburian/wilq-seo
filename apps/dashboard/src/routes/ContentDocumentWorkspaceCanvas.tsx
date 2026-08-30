import { useEffect, useRef, useState, type ReactNode } from "react";

import type { ContentSelectedWorkspace } from "../lib/api";
import {
  useContentRevisionTargetDraftPreview,
  useContentRevisionTargetMapping,
  useContentTargetDiscovery
} from "./contentWorkflowQueries";
import { ContentApprovedHtmlPackage } from "./ContentApprovedHtmlPackage";
import { ContentOperatorJourney } from "./ContentOperatorJourney";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";
import { ContentDocumentPreparationAction } from "./DocumentCanvasSections/PreparationSection";
import {
  DevTargetDetails,
  TargetDraftPreviewDetails,
  TargetMappingDetails
} from "./DocumentCanvasSections/TargetSections";
import type { ContentDocumentWorkspace } from "./DocumentCanvasSections/shared";

export { DevTargetLivePreview } from "./DocumentCanvasSections/TargetSections";

type View = "source" | "document" | "comparison";

export function ContentDocumentWorkspaceCanvas({
  workspace,
  operatorJourney,
  requestedBy,
  onOpenReview,
  leadingPanel
}: {
  workspace: ContentDocumentWorkspace;
  operatorJourney: ContentSelectedWorkspace["operator_journey"];
  requestedBy: string;
  onOpenReview: () => void;
  leadingPanel?: ReactNode;
}) {
  const hasDocument = Boolean(workspace.canonical_document.preview);
  const [view, setView] = useState<View>(() => hasDocument ? "document" : "source");
  const hadDocument = useRef(hasDocument);
  useEffect(() => {
    if (hasDocument && !hadDocument.current) setView("document");
    hadDocument.current = hasDocument;
  }, [hasDocument]);
  const [devDetailsOpen, setDevDetailsOpen] = useState(false);
  const [mappingOpen, setMappingOpen] = useState(false);
  const [draftPreviewOpen, setDraftPreviewOpen] = useState(false);
  const devDraftStep = operatorJourney.steps.find((step) => step.id === "dev_draft");
  const devDraftCanOpen = devDraftStep?.can_open === true && devDraftStep.readiness === "ready";
  const targetDiscovery = useContentTargetDiscovery(workspace.work_item_id, devDetailsOpen);
  const targetMapping = useContentRevisionTargetMapping(
    workspace.work_item_id,
    workspace.canonical_document.revision_id ?? null,
    mappingOpen && devDraftCanOpen
  );
  const targetDraftPreview = useContentRevisionTargetDraftPreview(
    workspace.work_item_id,
    workspace.canonical_document.revision_id ?? null,
    draftPreviewOpen && devDraftCanOpen
  );
  const nextActionHandler = actionForNextStep(
    workspace.next_action.kind,
    onOpenReview
  );
  const distinctNoActionReason = workspace.next_action.kind === "none" &&
    workspace.next_action.reason !== workspace.canonical_document.reason;

  return (
    <main className="mx-auto max-w-[92rem] px-4 py-5 lg:px-8" data-testid="content-text-workspace">
      <ContentWorkflowWorkspaceHeader />
      {leadingPanel ? <div className="mt-4">{leadingPanel}</div> : null}
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Praca nad treścią</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
              {workspace.source_snapshot.title ?? "Wybrana strona"}
            </h2>
            {workspace.source_snapshot.url ? (
              <a className="mt-2 block break-all text-sm font-medium text-action hover:underline" href={workspace.source_snapshot.url} target="_blank" rel="noreferrer">
                {workspace.source_snapshot.url}
              </a>
            ) : null}
            <p className="mt-2 text-sm font-medium text-slate-700">Usługa: {workspace.service_label ?? "niepotwierdzona"}</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
              W jednym miejscu sprawdzisz obecną stronę, stan nowego dokumentu i dostępne porównanie. To nie zmienia WordPressa.
            </p>
          </div>
          <section className="min-w-64 rounded-xl border border-line bg-surface p-4" data-testid="content-document-state">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Stan nowej wersji</p>
            <p className="mt-2 text-base font-semibold text-ink">{workspace.canonical_document.label}</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{workspace.canonical_document.reason}</p>
            {workspace.next_action.kind === "prepare_document" ? (
              <ContentDocumentPreparationAction
                workspace={workspace}
                requestedBy={requestedBy}
                onPrepared={() => setView("document")}
              />
            ) : nextActionHandler ? (
              <button type="button" className="mt-3 w-full rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={nextActionHandler}>
                {workspace.next_action.label}
              </button>
            ) : null}
            {distinctNoActionReason ? (
              <p className="mt-3 rounded-md border border-line bg-white p-3 text-sm leading-5 text-slate-700">{workspace.next_action.reason}</p>
            ) : null}
          </section>
        </div>
      </section>

      <ContentOperatorJourney journey={operatorJourney} />

      <nav className="mt-4 flex gap-1 border-b border-line" aria-label="Widok dokumentu">
        <Tab active={view === "source"} onClick={() => setView("source")}>Obecna strona</Tab>
        <Tab active={view === "document"} onClick={() => setView("document")}>Nowa wersja</Tab>
        <Tab active={view === "comparison"} onClick={() => setView("comparison")}>Porównanie</Tab>
      </nav>

      <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <section className="min-w-0 rounded-2xl border border-line bg-white p-5 shadow-sm lg:p-7" data-testid="content-workspace-canvas">
          {view === "source" ? <CurrentSource workspace={workspace} /> : null}
          {view === "document" ? <CanonicalDocument workspace={workspace} /> : null}
          {view === "comparison" ? <Comparison workspace={workspace} /> : null}
        </section>
        <aside className="rounded-2xl border border-line bg-white p-4 shadow-sm" aria-label="Szczegóły i dev">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Szczegóły i dev</p>
          <StatusCard label="Materiał obecnej strony" value={workspace.source_snapshot.status_label} />
          {workspace.canonical_document.status === "approved" && workspace.canonical_document.revision_id && workspace.canonical_document.content_digest ? (
            <ContentApprovedHtmlPackage
              workItemId={workspace.work_item_id}
              revisionId={workspace.canonical_document.revision_id}
              revisionDigest={workspace.canonical_document.content_digest}
            />
          ) : null}
          <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700">
            <summary className="cursor-pointer font-semibold text-ink">Źródła i ograniczenia</summary>
            <p className="mt-3 leading-6">{workspace.source_snapshot.reason}</p>
            {workspace.secondary_disclosures.map((detail) => <p key={detail} className="mt-3 leading-6">{detail}</p>)}
            <EditorialProvenance provenance={workspace.canonical_document.source_provenance ?? []} />
          </details>
          <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" onToggle={(event) => {
            if ((event.currentTarget as HTMLDetailsElement).open) setDevDetailsOpen(true);
          }}>
            <summary className="cursor-pointer font-semibold text-ink">Strona robocza na dev</summary>
            {!devDetailsOpen ? <p className="mt-3 leading-6">Otwórz, aby sprawdzić, co WILQ odczytał na dev. To nie zmienia strony ani nie uruchamia WordPressa.</p> : null}
            {targetDiscovery.isPending ? <p className="mt-3 leading-6">Wczytuję odczyt strony roboczej na dev…</p> : null}
            {targetDiscovery.isError ? <p className="mt-3 leading-6">Nie udało się odczytać strony roboczej na dev. Spróbuj ponownie później.</p> : null}
            {targetDiscovery.data ? <DevTargetDetails discovery={targetDiscovery.data} /> : null}
          </details>
          {devDraftCanOpen ? <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" onToggle={(event) => {
            if ((event.currentTarget as HTMLDetailsElement).open) setMappingOpen(true);
          }}>
            <summary className="cursor-pointer font-semibold text-ink">Przypisanie dokumentu do dev</summary>
            {!mappingOpen ? <p className="mt-3 leading-6">Otwórz, aby sprawdzić, które elementy zatwierdzonego dokumentu wymagają jeszcze potwierdzenia w układzie dev.</p> : null}
            {mappingOpen && targetMapping.isPending ? <p className="mt-3 leading-6">Sprawdzam przypisanie zatwierdzonego dokumentu…</p> : null}
            {mappingOpen && targetMapping.isError ? <p className="mt-3 leading-6">Nie udało się odczytać przypisania dokumentu. Spróbuj ponownie później.</p> : null}
            {mappingOpen && targetMapping.data ? <TargetMappingDetails preview={targetMapping.data} /> : null}
          </details> : null}
          {devDraftCanOpen ? <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" onToggle={(event) => {
            if ((event.currentTarget as HTMLDetailsElement).open) setDraftPreviewOpen(true);
          }}>
            <summary className="cursor-pointer font-semibold text-ink">Podgląd danych do szkicu na dev</summary>
            {!draftPreviewOpen ? <p className="mt-3 leading-6">Otwórz po potwierdzeniu przypisania, aby zobaczyć dane przygotowane z dokładnej wersji dokumentu. To nadal nie tworzy szkicu.</p> : null}
            {draftPreviewOpen && targetDraftPreview.isPending ? <p className="mt-3 leading-6">Przygotowuję podgląd danych do szkicu…</p> : null}
            {draftPreviewOpen && targetDraftPreview.isError ? <p className="mt-3 leading-6">Nie udało się przygotować podglądu danych. Spróbuj ponownie później.</p> : null}
            {draftPreviewOpen && targetDraftPreview.data ? <TargetDraftPreviewDetails preview={targetDraftPreview.data} /> : null}
          </details> : null}
        </aside>
      </section>
    </main>
  );
}

export function ContentDocumentLineageDisclosure({ workspace }: { workspace: ContentDocumentWorkspace }) {
  const provenance = workspace.canonical_document.source_provenance ?? [];
  return <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" data-testid="content-document-lineage">
    <summary className="cursor-pointer font-semibold text-ink">Pochodzenie źródeł dokumentu</summary>
    {provenance.length === 0 ? <p className="mt-3">Brak zapisanej listy provenance dla tej rewizji.</p> : (
      <ul className="mt-3 space-y-2">{provenance.map((item) => <li key={`${item.source_fact_id}-${item.freshness_date}`}>
        {item.source_fact_id} · {item.freshness_date}
      </li>)}</ul>
    )}
  </details>;
}

function EditorialProvenance({
  provenance
}: {
  provenance: NonNullable<ContentDocumentWorkspace["canonical_document"]["source_provenance"]>;
}) {
  if (provenance.length === 0) {
    return <p className="mt-3 leading-6 text-slate-600">Brak zapisanej daty świeżości i weryfikacji eksperckiej dla tej rewizji.</p>;
  }
  return <div className="mt-3 rounded-lg bg-slate-50 p-3">
    <p className="font-semibold text-ink">Aktualność i weryfikacja</p>
    {provenance.map((item) => <p key={item.source_fact_id} className="mt-2 leading-6">
      {item.freshness_date} · {item.reviewer ? `weryfikacja: ${item.reviewer}` : "brak przypisanego eksperta"}
    </p>)}
  </div>;
}

function actionForNextStep(
  kind: ContentDocumentWorkspace["next_action"]["kind"],
  onOpenReview: () => void
): (() => void) | null {
  switch (kind) {
    case "open_review":
    case "repair_document":
      return onOpenReview;
    case "prepare_document":
      return null;
    case "none":
      return null;
    default:
      return kind satisfies never;
  }
}

function Tab({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button type="button" className={`border-b-2 px-4 py-3 text-sm font-semibold ${active ? "border-action text-action" : "border-transparent text-slate-600 hover:text-ink"}`} onClick={onClick}>{children}</button>;
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return <div className="mt-4 rounded-xl bg-slate-50 p-3"><p className="text-sm font-semibold text-ink">{label}</p><p className="mt-1 text-sm text-slate-700">{value}</p></div>;
}

function CurrentSource({ workspace }: { workspace: ContentDocumentWorkspace }) {
  return <div data-testid="content-source-snapshot">
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Obecna strona</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{workspace.source_snapshot.title ?? "Publiczny materiał źródłowy"}</h2>
    <p className="mt-3 text-sm leading-6 text-slate-700">{workspace.source_snapshot.reason}</p>
    {workspace.source_snapshot.lead ? <p className="mt-6 border-l-2 border-action/40 pl-4 text-base leading-7 text-slate-700">{workspace.source_snapshot.lead}</p> : null}
    <div className="mt-7 space-y-5">
      {workspace.source_snapshot.ordered_sections.map((section, index) => (
        <section key={`${section.heading}-${index}`} className="border-t border-line pt-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{index + 1}. fragment obecnej strony</p>
          <h3 className="mt-2 text-lg font-semibold text-ink">{section.heading}</h3>
          <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-700">{section.excerpt ?? "WILQ odczytał ten nagłówek, ale nie ma bezpiecznego wycinka tekstu do pokazania."}</p>
        </section>
      ))}
    </div>
  </div>;
}

function CanonicalDocument({ workspace }: { workspace: ContentDocumentWorkspace }) {
  const preview = workspace.canonical_document.preview;
  if (!preview) return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Nowa wersja</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{workspace.canonical_document.label}</h2>
    <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">{workspace.canonical_document.reason}</p>
    <div className="mt-6 rounded-xl border border-wait/25 bg-wait/5 p-4 text-sm leading-6 text-slate-700"><p className="font-semibold text-ink">Następny krok</p><p className="mt-1">{workspace.next_action.reason}</p></div>
  </>;
  return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Nowa wersja</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{preview.h1 ?? preview.title}</h2>
    {preview.lead ? <p className="mt-4 text-base leading-7 text-slate-700">{preview.lead}</p> : null}
    <p className="mt-4 text-sm text-slate-600">{preview.sections.length} sekcji · {preview.faq_count} pytań i odpowiedzi · {preview.cta_count} wezwań do działania</p>
    <div className="mt-7 space-y-7">{preview.sections.map((section) => <section key={section.section_id ?? section.heading} className="border-t border-line pt-6"><h3 className="text-xl font-semibold text-ink">{section.heading}</h3><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{section.body_markdown}</p></section>)}</div>
  </>;
}

function Comparison({ workspace }: { workspace: ContentDocumentWorkspace }) {
  if (workspace.comparison.status === "unavailable") return <><p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Porównanie</p><h2 className="mt-2 text-2xl font-semibold text-ink">Nie ma jeszcze czego porównać</h2><p className="mt-3 text-sm leading-6 text-slate-700">{workspace.comparison.reason}</p></>;
  return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Porównanie</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">Co zmienia się między wersjami</h2>
    <p className="mt-3 text-sm leading-6 text-slate-700">{workspace.comparison.reason}</p>
    <div className="mt-6 space-y-4">{workspace.comparison.items.map((item, index) => <article key={`${item.status}-${item.source_heading ?? item.document_heading}-${index}`} className="rounded-xl border border-line p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{comparisonLabel(item.status)}</p><div className="mt-3 grid gap-4 lg:grid-cols-2"><ComparisonSide label="Obecna strona" heading={item.source_heading} excerpt={item.source_excerpt} empty="Brak bezpośrednio rozpoznanego elementu." /><ComparisonSide label="Nowa wersja" heading={item.document_heading} excerpt={item.document_excerpt} empty="Brak bezpośrednio rozpoznanego elementu." /></div><p className="mt-4 text-sm leading-6 text-slate-600">{item.reason}</p></article>)}</div>
  </>;
}

function ComparisonSide({ label, heading, excerpt, empty }: { label: string; heading: string | null | undefined; excerpt: string | null | undefined; empty: string }) {
  return <section className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>{heading ? <h3 className="mt-2 text-sm font-semibold text-ink">{heading}</h3> : null}<p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{excerpt ?? empty}</p></section>;
}

function comparisonLabel(status: "same_heading" | "source_only" | "document_only") {
  return { same_heading: "ten sam nagłówek", source_only: "tylko na obecnej stronie", document_only: "tylko w nowej wersji" }[status];
}
