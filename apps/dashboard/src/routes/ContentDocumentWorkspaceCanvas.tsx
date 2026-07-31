import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { postContentWorkItemOfficialSourceLineageRebase, type ContentDocumentWorkspace } from "../lib/api";
import { ContentTextPreparationPanel } from "./ContentTextPreparationPanel";
import { ContentRevisionRepairPanel } from "./ContentRevisionRepairPanel";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";

type View = "source" | "document" | "comparison";

export function ContentDocumentWorkspaceCanvas({
  workspace,
  onOpenReview,
  operatorLabel,
  onWorkspaceChanged
}: {
  workspace: ContentDocumentWorkspace;
  onOpenReview: () => void;
  operatorLabel: string | null;
  onWorkspaceChanged: () => void;
}) {
  const [view, setView] = useState<View>(() =>
    workspace.canonical_document.preview ? "document" : "source"
  );
  const previousRevisionId = useRef(workspace.canonical_document.revision_id);
  useEffect(() => {
    const revisionId = workspace.canonical_document.revision_id;
    if (revisionId !== previousRevisionId.current && workspace.canonical_document.preview) {
      setView("document");
    }
    previousRevisionId.current = revisionId;
  }, [workspace.canonical_document.preview, workspace.canonical_document.revision_id]);
  const hasReviewAction = workspace.next_action.kind === "open_review";
  const needsPlanning = workspace.canonical_document.status === "not_created";
  const canCompare = workspace.comparison.status === "available";

  return (
    <main className="mx-auto max-w-[92rem] px-4 py-5 lg:px-8" data-testid="content-text-workspace">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Praca nad treścią</p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
              {workspace.source_snapshot.title ?? "Wybrana strona"}
            </h1>
            {workspace.source_snapshot.url ? (
              <a className="mt-2 block break-all text-sm font-medium text-action hover:underline" href={workspace.source_snapshot.url} target="_blank" rel="noreferrer">
                {workspace.source_snapshot.url}
              </a>
            ) : null}
            <p className="mt-2 text-sm font-medium text-slate-700">Usługa: {workspace.service_label ?? "niepotwierdzona"}</p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
              W jednym miejscu sprawdzisz obecną stronę, dokładny stan dokumentu i materiały zapisane przy tej rewizji. To nie zmienia WordPressa.
            </p>
          </div>
          {!needsPlanning ? (
            <section className="min-w-64 rounded-xl border border-line bg-surface p-4" data-testid="content-document-state">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Stan tekstu</p>
              <p className="mt-2 text-base font-semibold text-ink">{workspace.canonical_document.label}</p>
              <p className="mt-1 text-sm leading-5 text-slate-700">{workspace.canonical_document.reason}</p>
              {hasReviewAction ? (
                <button type="button" className="mt-3 w-full rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onOpenReview}>
                  {workspace.next_action.label}
                </button>
              ) : null}
            </section>
          ) : null}
        </div>
      </section>

      {needsPlanning ? (
        <section className="mt-4 space-y-4">
          <ContentTextPreparationPanel workItemId={workspace.work_item_id} />
        </section>
      ) : null}

      <ContentRevisionRepairPanel
        key={workspace.canonical_document.revision_id ?? "no-revision"}
        workspace={workspace}
        operatorLabel={operatorLabel}
        onChanged={onWorkspaceChanged}
      />

      <nav className="mt-4 flex gap-1 border-b border-line" aria-label="Widok dokumentu">
        <Tab active={view === "source"} onClick={() => setView("source")}>Obecna strona</Tab>
        <Tab active={view === "document"} onClick={() => setView("document")}>Nowa wersja</Tab>
        {canCompare ? <Tab active={view === "comparison"} onClick={() => setView("comparison")}>Zmiany w treści</Tab> : null}
      </nav>

      <section className="mt-4 grid gap-4 xl:grid-cols-[17rem_minmax(0,1fr)_18rem]">
        <section className="order-1 min-w-0 rounded-2xl border border-line bg-white p-5 shadow-sm lg:p-7 xl:order-2" data-testid="content-workspace-canvas">
          {view === "source" ? <CurrentSource workspace={workspace} /> : null}
          {view === "document" ? <CanonicalDocument workspace={workspace} onWorkspaceChanged={onWorkspaceChanged} /> : null}
          {view === "comparison" ? <Comparison workspace={workspace} /> : null}
        </section>
        <aside className="order-2 rounded-2xl border border-line bg-white p-4 shadow-sm xl:order-1" aria-label="Struktura strony">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Struktura strony</p>
          <p className="mt-2 text-sm leading-6 text-slate-700">{outlineLead(view)}</p>
          <ol className="mt-4 space-y-2">
            {outline(view, workspace).map((label, index) => (
              <li key={`${label}-${index}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm leading-5 text-slate-700">
                <span className="mr-2 font-semibold text-slate-500">{index + 1}.</span>{label}
              </li>
            ))}
          </ol>
        </aside>
        <aside className="order-3 rounded-2xl border border-line bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Kontekst pracy</p>
          <StatusCard label="Materiał obecnej strony" value={sourceStatus(workspace.source_snapshot.status)} />
          <StatusCard label="Nowy dokument" value={documentStatus(workspace.canonical_document.status)} />
          <ContentDocumentLineageDisclosure workspace={workspace} />
          <details className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700">
            <summary className="cursor-pointer font-semibold text-ink">Źródła i ograniczenia</summary>
            <p className="mt-3 leading-6">{workspace.source_snapshot.reason}</p>
            {workspace.secondary_disclosures.map((detail) => <p key={detail} className="mt-3 leading-6">{detail}</p>)}
          </details>
        </aside>
      </section>
    </main>
  );
}

function Tab({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button type="button" className={`border-b-2 px-4 py-3 text-sm font-semibold ${active ? "border-action text-action" : "border-transparent text-slate-600 hover:text-ink"}`} onClick={onClick}>{children}</button>;
}

function StatusCard({ label, value }: { label: string; value: string }) {
  return <div className="mt-4 rounded-xl bg-slate-50 p-3"><p className="text-sm font-semibold text-ink">{label}</p><p className="mt-1 text-sm text-slate-700">{value}</p></div>;
}

function outlineLead(view: View) {
  return { source: "To, co jest dziś widoczne na publicznej stronie.", document: "Układ przygotowanej wersji dokumentu.", comparison: "Zaobserwowane zmiany nagłówków i fragmentów, bez oceny wyglądu ani znaczenia." }[view];
}

function outline(view: View, workspace: ContentDocumentWorkspace): string[] {
  if (view === "source") return workspace.source_snapshot.ordered_sections.map((section) => section.heading);
  if (view === "document") return workspace.canonical_document.preview?.sections.map((section) => section.heading) ?? [workspace.canonical_document.label];
  return workspace.comparison.items.map((item) => item.document_heading ?? item.source_heading ?? "Element bez nazwy");
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

function CanonicalDocument({ workspace, onWorkspaceChanged }: { workspace: ContentDocumentWorkspace; onWorkspaceChanged: () => void }) {
  const preview = workspace.canonical_document.preview;
  if (!preview) return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Nowa wersja</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{workspace.canonical_document.label}</h2>
    <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">{workspace.canonical_document.reason}</p>
    <div className="mt-6 rounded-xl border border-wait/25 bg-wait/5 p-4 text-sm leading-6 text-slate-700"><p className="font-semibold text-ink">Co jest potrzebne do tekstu</p><p className="mt-1">{workspace.next_action.reason}</p></div>
  </>;
  return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Nowa wersja</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">{preview.h1 ?? preview.title}</h2>
    {preview.lead ? <p className="mt-4 text-base leading-7 text-slate-700">{preview.lead}</p> : null}
    <p className="mt-4 text-sm text-slate-600">{preview.sections.length} sekcji · {preview.faq_count} pytań i odpowiedzi · {preview.cta_count} wezwań do działania</p>
    <div className="mt-7 space-y-7">{preview.sections.map((section) => <section key={section.section_id ?? section.heading} className="border-t border-line pt-6"><h3 className="text-xl font-semibold text-ink">{section.heading}</h3><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{section.body_markdown}</p></section>)}</div>
    <OfficialSourceReferences references={workspace.canonical_document.revision?.official_source_references ?? []} />
    <OfficialSourceLineageRebase workspace={workspace} onWorkspaceChanged={onWorkspaceChanged} />
  </>;
}

function OfficialSourceLineageRebase({ workspace, onWorkspaceChanged }: { workspace: ContentDocumentWorkspace; onWorkspaceChanged: () => void }) {
  const revision = workspace.canonical_document.revision;
  const [message, setMessage] = useState<string | null>(null);
  const eligible = revision?.schema_version === "wilq_content_draft_revision_v2"
    && revision.official_source_references.length === 0
    && (workspace.canonical_document.status === "unreviewed" || workspace.canonical_document.status === "deferred");
  const rebase = useMutation({
    mutationFn: () => postContentWorkItemOfficialSourceLineageRebase({
      expected_revision_digest: revision!.content_digest,
      requested_by: "wilku"
    }, workspace.work_item_id, revision!.revision_id),
    onSuccess: (result) => {
      if (result.status === "conflict") {
        setMessage(result.safe_next_step);
        return;
      }
      setMessage("Utworzono nową, niezatwierdzoną rewizję z zapisanymi źródłami urzędowymi. Tekst nie został zmieniony.");
      onWorkspaceChanged();
    },
    onError: () => setMessage("Nie udało się uzupełnić źródeł. Odśwież dokument i spróbuj ponownie.")
  });
  if (!eligible) return null;
  return <section className="mt-8 rounded-xl border border-wait/25 bg-wait/5 p-4" data-testid="content-official-source-lineage-rebase">
    <p className="font-semibold text-ink">Brakuje zapisanych źródeł urzędowych</p>
    <p className="mt-1 text-sm leading-6 text-slate-700">WILQ sprawdzi bieżący plan i dopisze nową rewizję z jego źródłami. Nie zmieni tekstu ani WordPressa.</p>
    <button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={rebase.isPending} onClick={() => rebase.mutate()}>
      {rebase.isPending ? "Uzupełniam źródła…" : "Uzupełnij źródła urzędowe"}
    </button>
    {message ? <p className="mt-3 text-sm leading-6 text-slate-700">{message}</p> : null}
  </section>;
}

function OfficialSourceReferences({
  references
}: {
  references: NonNullable<ContentDocumentWorkspace["canonical_document"]["revision"]>["official_source_references"];
}) {
  const visibleReferences = references.filter((reference) => (
    reference.source_title.trim().length > 0
    && reference.source_url.trim().length > 0
    && reference.verified_on.trim().length > 0
    && reference.regulatory_requirement_ids.length > 0
  ));
  if (!visibleReferences.length) return null;

  return <section className="mt-8 rounded-xl border border-line bg-slate-50 p-4" data-testid="content-official-sources">
    <p className="font-semibold text-ink">Źródła urzędowe</p>
    <p className="mt-1 text-sm leading-6 text-slate-700">Źródła użyte do weryfikacji tej dokładnej wersji tekstu. Nie stanowią indywidualnej porady prawnej.</p>
    <ul className="mt-4 space-y-3">
      {visibleReferences.map((reference) => <li key={reference.source_fact_id} className="border-t border-line pt-3 first:border-t-0 first:pt-0">
        <a className="font-medium text-action underline underline-offset-2" href={reference.source_url} rel="noreferrer" target="_blank">{reference.source_title}</a>
        <p className="mt-1 text-sm text-slate-700">Zweryfikowano: {reference.verified_on}</p>
        <p className="mt-1 text-sm text-slate-600">Zakres weryfikacji: {regulatoryRequirementScope(reference.regulatory_requirement_ids.length)}.</p>
      </li>)}
    </ul>
  </section>;
}

function regulatoryRequirementScope(count: number) {
  if (count === 1) return "1 zagadnienie regulacyjne";
  if (count >= 2 && count <= 4) return `${count} zagadnienia regulacyjne`;
  return `${count} zagadnień regulacyjnych`;
}

export function ContentDocumentLineageDisclosure({ workspace }: { workspace: ContentDocumentWorkspace }) {
  const lineage = workspace.document_lineage;
  const contentCards = lineage.knowledge_cards.filter((card) => card.card_type !== "evidence_requirement");
  const safetyCardCount = lineage.knowledge_cards.length - contentCards.length;
  return <section className="mt-3 rounded-xl border border-line p-3 text-sm text-slate-700" data-testid="content-document-lineage">
    <p className="font-semibold text-ink">Na czym oparto tekst</p>
    <p className="mt-2 leading-6">{lineage.reason}</p>
    {contentCards.length ? <ul className="mt-3 space-y-3">
      {contentCards.map((card) => <li key={card.id} className="rounded-lg bg-slate-50 p-3">
        <p className="font-semibold text-ink">{card.title}</p>
        <p className="mt-1 leading-6">{card.summary}</p>
      </li>)}
    </ul> : null}
    {lineage.source_material_ids.length ? <p className="mt-3 leading-6">Zapisane materiały źródłowe: {lineage.source_material_ids.length}.</p> : null}
    {safetyCardCount ? <p className="mt-3 leading-6 text-slate-600">WILQ zastosował też {safetyCardCount === 1 ? "kontrolę" : `${safetyCardCount} kontrole`} źródeł i zasad tekstu.</p> : null}
    {lineage.unresolved_knowledge_card_ids.length ? <p className="mt-3 leading-6 text-wait">Nie można obecnie odczytać {lineage.unresolved_knowledge_card_ids.length} przypisanych kart wiedzy.</p> : null}
  </section>;
}

function Comparison({ workspace }: { workspace: ContentDocumentWorkspace }) {
  if (workspace.comparison.status === "unavailable") return <><p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Zmiany w treści</p><h2 className="mt-2 text-2xl font-semibold text-ink">Nie ma jeszcze czego zestawić</h2><p className="mt-3 text-sm leading-6 text-slate-700">{workspace.comparison.reason}</p></>;
  return <>
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Zmiany w treści</p>
    <h2 className="mt-2 text-2xl font-semibold text-ink">Co zmienia się między wersjami</h2>
    <p className="mt-3 text-sm leading-6 text-slate-700">{workspace.comparison.reason} WILQ zestawia tylko bezpośrednio zaobserwowane nagłówki i fragmenty — nie porównuje wyglądu strony ani znaczenia tekstu.</p>
    <div className="mt-6 space-y-4">{workspace.comparison.items.map((item, index) => <article key={`${item.status}-${item.source_heading ?? item.document_heading}-${index}`} className="rounded-xl border border-line p-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{comparisonLabel(item.status)}</p><div className="mt-3 grid gap-4 lg:grid-cols-2"><ComparisonSide label="Obecna strona" heading={item.source_heading} excerpt={item.source_excerpt} empty="Brak bezpośrednio rozpoznanego elementu." /><ComparisonSide label="Nowa wersja" heading={item.document_heading} excerpt={item.document_excerpt} empty="Brak bezpośrednio rozpoznanego elementu." /></div><p className="mt-4 text-sm leading-6 text-slate-600">{item.reason}</p></article>)}</div>
  </>;
}

function ComparisonSide({ label, heading, excerpt, empty }: { label: string; heading: string | null | undefined; excerpt: string | null | undefined; empty: string }) {
  return <section className="rounded-lg bg-slate-50 p-3"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>{heading ? <h3 className="mt-2 text-sm font-semibold text-ink">{heading}</h3> : null}<p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{excerpt ?? empty}</p></section>;
}

function comparisonLabel(status: "same_heading" | "source_only" | "document_only") {
  return { same_heading: "ten sam nagłówek", source_only: "tylko na obecnej stronie", document_only: "tylko w nowej wersji" }[status];
}

function sourceStatus(status: "available" | "partial" | "unavailable") {
  return { available: "materiał dostępny", partial: "materiał częściowy", unavailable: "materiał niedostępny" }[status];
}

function documentStatus(status: "not_created" | "unreviewed" | "needs_changes" | "approved" | "rejected" | "deferred") {
  return { not_created: "nie utworzono", unreviewed: "czeka na review", needs_changes: "wymaga zmian", approved: "zatwierdzony", rejected: "odrzucony", deferred: "odłożony" }[status];
}
