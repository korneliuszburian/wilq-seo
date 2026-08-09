import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import {
  getContentNewPageCanonicalDocument,
  reviewContentNewPageRevision,
  type ContentDraftRevision,
  type ContentNewPageCanonicalDocumentWorkspace
} from "../../lib/api";
import { ContentFullPagePreview } from "../ContentFullPagePreview";
import { InfoTile } from "./Shared";

export function useNewPageCanonicalDocument(briefId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["content-workflow", "new-page-brief", briefId, "canonical-document"],
    queryFn: () => getContentNewPageCanonicalDocument(briefId),
    enabled,
    staleTime: 15_000
  });
}

export function NewPageCanonicalDocument({
  document,
  onChanged
}: {
  document: ReturnType<typeof useNewPageCanonicalDocument>;
  onChanged: () => void;
}) {
  if (document.isLoading) return <p className="mt-4 text-sm text-slate-600">Sprawdzam stan dokumentu…</p>;
  if (document.error || !document.data) return <p className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-3 text-sm text-ink">Nie udało się odczytać kanonicznego dokumentu. Brief i dane źródłowe nie zostały przez to zmienione.</p>;
  return <>
    <NewPageDocumentState workspace={document.data} />
    <NewPageDocumentPreview revision={document.data.canonical_revision} />
    <NewPageDocumentCommands briefId={document.data.brief_id} workspace={document.data} onChanged={onChanged} />
  </>;
}

function NewPageDocumentPreview({ revision }: { revision: ContentDraftRevision | null | undefined }) {
  if (!revision) return null;
  if (!revision.page_assets) {
    return <section className="mt-4 rounded-xl border border-wait/30 bg-wait/5 p-4 text-sm leading-6 text-ink" data-testid="new-page-document-preview-blocker">
      <p className="font-semibold">Nie można jeszcze pokazać pełnej wersji tekstu</p>
      <p className="mt-1">Brakuje renderowalnych elementów strony dla tej rewizji. WILQ nie udostępni review, dopóki tekst nie będzie można przeczytać w całości.</p>
    </section>;
  }
  return <section className="mt-4" data-testid="new-page-document-preview">
    <ContentFullPagePreview revision={revision} />
  </section>;
}

function NewPageDocumentState({ workspace }: { workspace: ContentNewPageCanonicalDocumentWorkspace }) {
  const revision = workspace.canonical_revision;
  const lineage = workspace.document_lineage;
  return <section className="mt-5 rounded-2xl border border-sky-200 bg-sky-50/50 p-4" data-testid="new-page-canonical-document">
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-action">Kanoniczny dokument</p>
    <h3 className="mt-2 text-lg font-semibold text-ink">{workspace.title}</h3>
    <p className="mt-2 text-sm leading-6 text-slate-700">{documentStateCopy(workspace)}</p>
    <dl className="mt-4 grid gap-3 sm:grid-cols-2">
      <InfoTile label="Stan dokumentu" value={documentStatusLabel(workspace.document_status)} />
      <InfoTile label="Źródło publiczne" value="Nie dotyczy — to nowa strona." />
      <InfoTile label="Rewizja" value={revision ? `${revision.revision_id} · ${revision.content_digest.slice(0, 12)}…` : "Nie utworzono"} />
      <InfoTile label="Review" value={workspace.revision_review ? reviewLabel(workspace.revision_review.decision) : "Nie zapisano"} />
    </dl>
    <details className="mt-4 rounded-xl border border-sky-200 bg-white px-3 py-2" data-testid="new-page-document-lineage">
      <summary className="cursor-pointer text-sm font-semibold text-ink">Materiały i wiedza użyte w tej wersji</summary>
      <p className="mt-2 text-sm leading-6 text-slate-700">{lineage.reason}</p>
      {lineage.knowledge_cards.length ? <ul className="mt-3 space-y-2">{lineage.knowledge_cards.map((card) => <li key={card.id} className="rounded-lg bg-slate-50 px-3 py-2"><p className="text-sm font-semibold text-ink">{card.title}</p><p className="mt-1 text-xs leading-5 text-slate-600">{card.summary}</p></li>)}</ul> : null}
      {lineage.source_material_ids.length ? <p className="mt-3 text-xs leading-5 text-slate-600">Zapisane materiały: {lineage.source_material_ids.join(", ")}</p> : null}
      {lineage.unresolved_knowledge_card_ids.length ? <p className="mt-3 text-xs leading-5 text-wait">Nie można już odczytać części zapisanych kart: {lineage.unresolved_knowledge_card_ids.join(", ")}. WILQ nie zastępuje ich globalnym katalogiem.</p> : null}
    </details>
    <p className="mt-4 text-xs leading-5 text-slate-600">To nie jest porównanie z obecną stroną ani potwierdzenie publikacji. WILQ nie tworzy tu szkicu WordPressa.</p>
  </section>;
}

function documentStateCopy(workspace: ContentNewPageCanonicalDocumentWorkspace) {
  if (!workspace.canonical_revision) {
    return "Po przygotowaniu tekst pojawi się tutaj w całości. WILQ nie tworzy jeszcze szkicu ani nie zmienia WordPressa.";
  }
  if (workspace.document_status === "unreviewed") {
    return "Przeczytaj przygotowany tekst i materiały, na których go oparto. Dopiero potem możesz zdecydować, czy ta wersja jest gotowa.";
  }
  if (workspace.document_status === "approved") {
    return "Ta wersja tekstu została sprawdzona. Dalsze przygotowanie szkicu na dev pozostaje osobnym, bezpiecznym działaniem.";
  }
  return "WILQ pokazuje dokładny stan tej wersji tekstu i zapisane przy niej materiały.";
}

function NewPageDocumentCommands({ briefId, workspace, onChanged }: { briefId: string; workspace: ContentNewPageCanonicalDocumentWorkspace; onChanged: () => void }) {
  if (workspace.status === "document_review_required" && workspace.canonical_revision) {
    if (!workspace.canonical_revision.page_assets) return null;
    return <NewPageRevisionReview briefId={briefId} workspace={workspace} onChanged={onChanged} />;
  }
  return null;
}

function NewPageRevisionReview({ briefId, workspace, onChanged }: { briefId: string; workspace: ContentNewPageCanonicalDocumentWorkspace; onChanged: () => void }) {
  const revision = workspace.canonical_revision!;
  const [decision, setDecision] = useState<"approved" | "needs_changes">("approved");
  const [notes, setNotes] = useState("");
  const evidenceIds = [...new Set(revision.sections.flatMap((section) => section.evidence_ids))];
  const review = useMutation({
    mutationFn: () => reviewContentNewPageRevision(briefId, revision.revision_id, {
      expected_revision_digest: revision.content_digest,
      reviewed_by: "wilku",
      decision,
      notes,
      checked_items: decision === "approved" ? ["Tekst sprawdzony względem briefu, wybranej wiedzy i przypisanych źródeł."] : [],
      evidence_ids: decision === "approved" ? evidenceIds : []
    }),
    onSuccess: onChanged
  });
  const approvalReady = decision !== "approved" || evidenceIds.length > 0;
  return <section className="mt-4 rounded-xl border border-amber-200 bg-amber-50/50 p-4" data-testid="new-page-revision-review">
    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-amber-800">Review dokumentu</p>
    <h4 className="mt-2 text-base font-semibold text-ink">Sprawdź tekst</h4>
    <p className="mt-1 text-sm leading-6 text-slate-700">Jeśli tekst odpowiada briefowi, wybranej wiedzy i źródłom, zatwierdź tę dokładną rewizję {revision.content_digest.slice(0, 12)}…</p>
    {decision === "needs_changes" ? <label className="mt-3 block text-sm font-semibold text-ink">Co poprawić w tekście?<textarea className="mt-1 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal" value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} /></label> : <p className="mt-3 text-sm leading-6 text-slate-700">Nie musisz wpisywać osoby oceniającej ani zaznaczać checklisty — zatwierdzenie zapisze exact rewizję z jej dowodami.</p>}
    <div className="mt-3 flex flex-wrap gap-3"><button type="button" className="rounded-xl bg-action px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" disabled={!approvalReady || (decision !== "approved" && !notes.trim()) || review.isPending} onClick={() => review.mutate()}>{review.isPending ? "Zapisuję review…" : decision === "approved" ? "Zatwierdź tekst" : "Zapisz uwagi"}</button>{decision === "approved" ? <button type="button" className="text-sm font-semibold text-action underline" disabled={review.isPending} onClick={() => setDecision("needs_changes")}>Tekst wymaga zmian</button> : <button type="button" className="text-sm font-semibold text-action underline" disabled={review.isPending} onClick={() => setDecision("approved")}>Wróć do zatwierdzania</button>}</div>
    {review.isError ? <p className="mt-2 text-sm leading-6 text-wait">Review nie został zapisany. Odśwież dokument — jego dokładna rewizja mogła się zmienić.</p> : null}
  </section>;
}

function documentStatusLabel(status: ContentNewPageCanonicalDocumentWorkspace["document_status"]) {
  return { not_created: "Nie utworzono", unreviewed: "Czeka na review", approved: "Zatwierdzona", needs_changes: "Wymaga zmian", rejected: "Odrzucona", deferred: "Odłożona" }[status];
}

function reviewLabel(decision: NonNullable<ContentNewPageCanonicalDocumentWorkspace["revision_review"]>["decision"]) {
  return { approved: "Zatwierdzone", needs_changes: "Wymaga zmian", rejected: "Odrzucone", deferred: "Odłożone" }[decision];
}
