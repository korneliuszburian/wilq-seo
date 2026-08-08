import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams, useRouterState } from "@tanstack/react-router";
import { useState } from "react";

import {
  saveContentWorkItemDraftRevisionReview,
  type ContentDraftRevision,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionReview,
  type ContentDraftRevisionReviewRequest
} from "../lib/api";
import { ContentDocumentLineageDisclosure, ContentDocumentWorkspaceCanvas } from "./ContentDocumentWorkspaceCanvas";
import { ContentFullPagePreview } from "./ContentFullPagePreview";
import { ContentApprovedHtmlPackage } from "./ContentApprovedHtmlPackage";
import { ContentEditorialIntegrityReport } from "./ContentEditorialIntegrityReport";
import { ContentSemanticReviewPanel } from "./ContentSemanticReviewPanel";
import { ContentRevisionRepairPanel } from "./ContentRevisionRepairPanel";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";
import {
  useContentWorkflowQueries,
  type ContentSelectedWorkspaceQuery,
  type ContentWorkflowEntryQuery,
  type ContentInventoryCatalogQuery
} from "./contentWorkflowQueries";

export function ContentWorkflowSurface() {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const routeParams = useParams({ strict: false }) as { workItemId?: string };
  const selectedWorkItemId = routeParams.workItemId ?? stringFromSearch(routeSearch, "work_item_id");
  const contentView = useRouterState({
    select: (state) => Reflect.get(state.location.search, "view")
  });
  const reviewOpen = useRouterState({
    select: (state) => Reflect.get(state.location.search, "view") === "review" || Reflect.get(state.location.search, "review") === 1
  });
  const browseInventory = useRouterState({
    select: (state) => Reflect.get(state.location.search, "view") === "browse" || Reflect.get(state.location.search, "browse") === 1
  });
  const newPageId = useRouterState({
    select: (state) => {
      const value = Reflect.get(state.location.search, "new_page");
      return typeof value === "string" && value ? value : null;
    }
  });
  const newPageOpen = contentView === "new" || Boolean(newPageId);
  const selectWorkItem = (workItemId: string) => {
    void navigate({
      to: "/content-workflow/$workItemId",
      params: { workItemId },
      search: (previous) => ({
        ...contentWorkflowSearch(previous),
        work_item_id: undefined,
        section_heading: undefined,
        planning_digest: undefined,
        workspace: undefined,
        text: undefined,
        review: undefined,
        browse: undefined,
        new_page: undefined
      })
    });
  };
  const {
    selectedWorkspace,
    entry,
    inventory,
    diagnostics,
    operatorContext
  } = useContentWorkflowQueries(
    selectedWorkItemId,
    browseInventory,
    !selectedWorkItemId && !newPageOpen && !browseInventory
  );

  return (
    <ContentWorkflowRouteState
      selectedWorkItemId={selectedWorkItemId}
      selectedWorkspace={selectedWorkspace}
      entry={entry}
      inventory={inventory}
      diagnostics={diagnostics}
      reviewOpen={reviewOpen}
      browseInventory={browseInventory}
      newPageOpen={newPageOpen}
      newPageId={newPageId}
      operatorLabel={operatorContext.data?.request_label ?? null}
      onSelectWorkItem={selectWorkItem}
      onBrowseInventory={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined, view: "browse" })
        });
      }}
      onOpenNewPage={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined, view: "new" })
        });
      }}
      onNewPageBriefSaved={(briefId) => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: briefId, view: "new" })
        });
      }}
      onCloseEntrySecondaryView={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined, view: undefined })
        });
      }}
      onOpenReview={(workItemId) => {
        void navigate({
          to: "/content-workflow/$workItemId",
          params: { workItemId },
          search: (previous) => ({
            work_item_id: undefined,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: undefined,
            review: undefined,
            browse: undefined,
            new_page: undefined,
            view: "review"
          })
        });
      }}
      onReturnToText={(workItemId) => {
        void navigate({
          to: "/content-workflow/$workItemId",
          params: { workItemId },
          search: (previous) => ({
            work_item_id: undefined,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: undefined,
            review: undefined,
            browse: undefined,
            new_page: undefined,
            view: undefined
          })
        });
      }}
    />
  );
}

function stringFromSearch(search: string, key: string) {
  const value = new URLSearchParams(search).get(key);
  return value || null;
}

function contentWorkflowSearch(previous: {
  work_item_id?: string;
  section_heading?: string;
  planning_digest?: string;
  workspace?: string;
  text?: 1;
  review?: 1;
  browse?: 1;
  new_page?: string;
  view?: "review" | "browse" | "new";
}) {
  return {
    work_item_id: previous.work_item_id,
    section_heading: previous.section_heading,
    planning_digest: previous.planning_digest,
    workspace: previous.workspace,
    text: previous.text,
    review: previous.review,
    browse: previous.browse,
    new_page: previous.new_page,
    view: previous.view
  };
}

function ContentWorkflowRouteState({
  selectedWorkItemId,
  selectedWorkspace,
  entry,
  inventory,
  diagnostics,
  reviewOpen,
  browseInventory,
  newPageOpen,
  newPageId,
  operatorLabel,
  onSelectWorkItem,
  onBrowseInventory,
  onOpenNewPage,
  onNewPageBriefSaved,
  onCloseEntrySecondaryView,
  onOpenReview,
  onReturnToText
}: {
  selectedWorkItemId: string | null;
  selectedWorkspace: ContentSelectedWorkspaceQuery;
  entry: ContentWorkflowEntryQuery;
  inventory: ContentInventoryCatalogQuery;
  diagnostics: ReturnType<typeof useContentWorkflowQueries>["diagnostics"];
  reviewOpen: boolean;
  browseInventory: boolean;
  newPageOpen: boolean;
  newPageId: string | null;
  operatorLabel: string | null;
  onSelectWorkItem: (workItemId: string) => void;
  onBrowseInventory: () => void;
  onOpenNewPage: () => void;
  onNewPageBriefSaved: (briefId: string) => void;
  onCloseEntrySecondaryView: () => void;
  onOpenReview: (workItemId: string) => void;
  onReturnToText: (workItemId: string) => void;
}) {
  if (!selectedWorkItemId) {
    if (newPageOpen) {
      return (
        <ContentWorkflowEntryPanel
          entry={entry.data ?? null}
          inventory={inventory.data ?? null}
          diagnostics={null}
          browseInventory={browseInventory}
          newPageOpen={newPageOpen}
          newPageId={newPageId}
          onBrowseInventory={onBrowseInventory}
          onCloseSecondaryView={onCloseEntrySecondaryView}
          onOpenNewPage={onOpenNewPage}
          onNewPageBriefSaved={onNewPageBriefSaved}
          onSelectWorkItem={onSelectWorkItem}
        />
      );
    }
    if (entry.isLoading) return <ContentWorkflowEntryPending />;
    if (entry.error || !entry.data) {
      return <ContentWorkflowEntryFailure onRetry={() => void entry.refetch()} />;
    }
    return (
      <ContentWorkflowEntryPanel
        entry={entry.data}
        inventory={inventory.data ?? null}
        diagnostics={diagnostics.data ?? null}
        browseInventory={browseInventory}
        newPageOpen={newPageOpen}
        newPageId={newPageId}
        onBrowseInventory={onBrowseInventory}
        onCloseSecondaryView={onCloseEntrySecondaryView}
        onOpenNewPage={onOpenNewPage}
        onNewPageBriefSaved={onNewPageBriefSaved}
        onSelectWorkItem={onSelectWorkItem}
      />
    );
  }
  if (!reviewOpen) {
    return (
      <ContentTextWorkspace
        workItemId={selectedWorkItemId}
        selectedWorkspace={selectedWorkspace}
        onOpenReview={onOpenReview}
      />
    );
  }
  return <ContentReviewRoute
    selectedWorkspace={selectedWorkspace}
    operatorLabel={operatorLabel}
    onReturnToText={onReturnToText}
  />;
}

function ContentWorkflowEntryPending() {
  return <main className="mx-auto min-h-screen max-w-7xl px-4 py-5 lg:px-8"><section className="rounded-2xl border border-line bg-white p-5 shadow-sm"><p className="text-lg font-semibold text-ink">Wczytuję wybór pracy…</p><p className="mt-2 text-sm text-slate-700">Pobieram dostępne tryby i sprawy do pracy. To nie jest błąd.</p></section></main>;
}

function ContentWorkflowEntryFailure({ onRetry }: { onRetry: () => void }) {
  return <main className="mx-auto min-h-screen max-w-7xl px-4 py-5 lg:px-8"><section className="rounded-2xl border border-wait/30 bg-white p-5 shadow-sm"><p className="text-lg font-semibold text-ink">Nie udało się wczytać wyboru pracy.</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie</button></section></main>;
}

function ContentTextWorkspace({
  workItemId,
  selectedWorkspace,
  onOpenReview
}: {
  workItemId: string;
  selectedWorkspace: ContentSelectedWorkspaceQuery;
  onOpenReview: (workItemId: string) => void;
}) {
  if (selectedWorkspace.isLoading) {
    return <DocumentWorkspacePending />;
  }
  if (selectedWorkspace.error || !selectedWorkspace.data || selectedWorkspace.data.status === "missing") {
    return <DocumentWorkspaceError onRetry={() => void selectedWorkspace.refetch()} />;
  }
  const workspace = selectedWorkspace.data.workspace;
  if (!workspace) return <DocumentWorkspaceError onRetry={() => void selectedWorkspace.refetch()} />;
  return <ContentDocumentWorkspaceCanvas
    workspace={workspace}
    operatorJourney={selectedWorkspace.data.operator_journey}
    onOpenReview={() => onOpenReview(workItemId)}
  />;
}

function DocumentWorkspacePending() {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-pending"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-line bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Wczytuję aktualną stronę…</p><p className="mt-2 text-sm text-slate-700">Pobieram materiał źródłowy i stan dokumentu. To nie jest błąd.</p></section></main>;
}

function DocumentWorkspaceError({ onRetry }: { onRetry: () => void }) {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-error"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-wait/30 bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Nie udało się odczytać workspace’u strony.</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie</button></section></main>;
}

function ContentReviewWorkspace({
  workspace,
  operatorLabel,
  onReturnToText
}: {
  workspace: NonNullable<NonNullable<ContentSelectedWorkspaceQuery["data"]>["workspace"]>;
  operatorLabel: string | null;
  onReturnToText: (workItemId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState<ContentDraftRevisionDecision>("approved");
  const [notes, setNotes] = useState("");
  const revision = workspace.canonical_document.revision ?? null;
  const completeRevision = revision?.page_assets ? revision : null;
  const persistedReview = workspace.canonical_document.review ?? null;
  const matchingReview = persistedReview && completeRevision &&
    persistedReview.revision_id === completeRevision.revision_id &&
    persistedReview.revision_digest === completeRevision.content_digest
    ? persistedReview
    : null;
  const evidenceIds = completeRevision ? revisionEvidenceIds(completeRevision) : [];
  const reviewAvailable = workspace.next_action.kind === "open_review";
  const reviewMutation = useMutation({
    mutationFn: (request: ContentDraftRevisionReviewRequest) =>
      saveContentWorkItemDraftRevisionReview(request, workspace.work_item_id, completeRevision!.revision_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["content-workflow", "work-item", workspace.work_item_id, "selected-workspace"]
      });
    }
  });
  const canSubmit = Boolean(
    completeRevision &&
      operatorLabel &&
      !matchingReview &&
      reviewAvailable &&
      !reviewMutation.isPending &&
      (decision === "approved"
        ? evidenceIds.length > 0
        : notes.trim().length > 0)
  );
  const submitReview = () => {
    if (!completeRevision || !operatorLabel || !canSubmit) return;
    reviewMutation.mutate({
      expected_revision_digest: completeRevision.content_digest,
      reviewed_by: operatorLabel,
      decision,
      notes: notes.trim(),
      checked_items: decision === "approved"
        ? ["Tekst sprawdzony przed zatwierdzeniem.", "Dowody tej rewizji sprawdzone przed zatwierdzeniem."]
        : [],
      evidence_ids: decision === "approved" ? evidenceIds : []
    });
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-review-workspace">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Sprawdź nową wersję</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
          {workspace.source_snapshot.title ?? "Wybrana strona"}
        </h1>
        {workspace.source_snapshot.url ? <p className="mt-2 break-all text-sm text-action">{workspace.source_snapshot.url}</p> : null}
        <p className="mt-2 text-sm font-medium text-slate-700">Usługa: {workspace.service_label ?? "niepotwierdzona"}</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">Przeczytaj przygotowany tekst i sprawdź materiały, na których go oparto. Zatwierdzenie dotyczy wyłącznie tej wersji tekstu — nie publikuje niczego.</p>
      </section>
      <section className="mt-4 rounded-2xl border border-line bg-white p-4 shadow-sm lg:p-5">
        {completeRevision ? (
          <>
            <ReviewDecisionPanel
              revision={completeRevision}
              matchingReview={matchingReview}
              hasOperatorIdentity={Boolean(operatorLabel)}
              decision={decision}
              notes={notes}
              canSubmit={canSubmit}
              reviewAvailable={reviewAvailable}
              isPending={reviewMutation.isPending}
              error={reviewMutation.error}
              result={reviewMutation.data}
              onDecisionChange={setDecision}
              onNotesChange={setNotes}
              onSubmit={submitReview}
              onReloadCurrent={() => {
                void queryClient.invalidateQueries({ queryKey: ["content-workflow", "work-item", workspace.work_item_id, "selected-workspace"] });
              }}
              onReturnToText={() => onReturnToText(workspace.work_item_id)}
            />
            <div className="mt-5">
              <ContentFullPagePreview revision={completeRevision} />
            </div>
            <details
              open
              className="mt-5 rounded-xl border border-line bg-slate-50 p-4 text-slate-700"
              data-testid="content-review-advisory"
            >
              <summary className="cursor-pointer font-semibold text-ink">Weryfikacja i poprawki</summary>
              <ContentClaimLedgerPanel revision={completeRevision} />
              <ContentDocumentLineageDisclosure workspace={workspace} />
              <ContentSemanticReviewPanel
                workItemId={workspace.work_item_id}
                revisionId={completeRevision.revision_id}
              />
              <ContentRevisionRepairPanel
                workspace={workspace}
                operatorLabel={operatorLabel}
                onChanged={() => {
                  void queryClient.invalidateQueries({ queryKey: ["content-workflow", "work-item", workspace.work_item_id, "selected-workspace"] });
                }}
              />
              {completeRevision.base_revision_id ? <ContentEditorialIntegrityReport workItemId={workspace.work_item_id} revisionId={completeRevision.revision_id} /> : null}
            </details>
          </>
        ) : (
          <div data-testid="content-review-blocker">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Stan review</p>
            <h2 className="mt-2 text-lg font-semibold text-ink">Pełna rewizja HTML — niegotowa do review</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {workspace.canonical_document.reason}
            </p>
          </div>
        )}
      </section>
      <details className="mt-4 rounded-xl border border-line bg-white p-4 text-sm text-slate-700">
        <summary className="cursor-pointer font-semibold text-ink">Szczegóły, źródła i ograniczenia</summary>
        <p className="mt-3 leading-6">{workspace.source_snapshot.reason}</p>
      </details>
    </main>
  );
}

function ContentClaimLedgerPanel({ revision }: { revision: ContentDraftRevision }) {
  const ledger = revision.claim_ledger;
  if (!ledger) return null;
  return (
    <section className="mt-4 rounded-xl border border-line bg-white p-4" data-testid="content-claim-ledger">
      <h2 className="text-base font-semibold text-ink">Twierdzenia i dowody</h2>
      <ul className="mt-3 space-y-3">
        {ledger.entries.map((entry) => (
          <li key={entry.id} className="rounded-lg border border-line p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="font-medium text-ink">{entry.claim_text}</p>
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                {contentClaimStatusLabel(entry.status)}
              </span>
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-600">
              Źródła: {entry.source_connectors.length > 0 ? entry.source_connectors.join(", ") : "brak"}
              {" · "}Dowody: {entry.evidence_ids.length}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function contentClaimStatusLabel(
  status: NonNullable<ContentDraftRevision["claim_ledger"]>["entries"][number]["status"]
) {
  switch (status) {
    case "allowed_with_evidence":
      return "z dowodem";
    case "blocked":
    case "blocked_until_measurement":
      return "blokuje";
    case "allowed_general":
    case "needs_human_review":
      return "brak dowodu";
    default:
      return status satisfies never;
  }
}

function ContentReviewRoute({
  selectedWorkspace,
  operatorLabel,
  onReturnToText
}: {
  selectedWorkspace: ContentSelectedWorkspaceQuery;
  operatorLabel: string | null;
  onReturnToText: (workItemId: string) => void;
}) {
  if (selectedWorkspace.isLoading) {
    return <DocumentWorkspacePending />;
  }
  if (selectedWorkspace.error || !selectedWorkspace.data || selectedWorkspace.data.status === "missing" || !selectedWorkspace.data.workspace) {
    return <DocumentWorkspaceError onRetry={() => void selectedWorkspace.refetch()} />;
  }
  return <ContentReviewWorkspace
    workspace={selectedWorkspace.data.workspace}
    operatorLabel={operatorLabel}
    onReturnToText={onReturnToText}
  />;
}

function ReviewDecisionPanel({
  revision,
  matchingReview,
  hasOperatorIdentity,
  decision,
  notes,
  canSubmit,
  reviewAvailable,
  isPending,
  error,
  result,
  onDecisionChange,
  onNotesChange,
  onSubmit,
  onReloadCurrent,
  onReturnToText
}: {
  revision: ContentDraftRevision;
  matchingReview: ContentDraftRevisionReview | null;
  hasOperatorIdentity: boolean;
  decision: ContentDraftRevisionDecision;
  notes: string;
  canSubmit: boolean;
  reviewAvailable: boolean;
  isPending: boolean;
  error: Error | null;
  result: Awaited<ReturnType<typeof saveContentWorkItemDraftRevisionReview>> | undefined;
  onDecisionChange: (decision: ContentDraftRevisionDecision) => void;
  onNotesChange: (notes: string) => void;
  onSubmit: () => void;
  onReloadCurrent: () => void;
  onReturnToText: () => void;
}) {
  const conflict = result?.status === "conflict" ? result : null;
  const savedReview = result && result.status !== "conflict" ? result.review : matchingReview;
  if (savedReview) {
    return (
      <div className="mt-5 rounded-xl border border-action/20 bg-action/5 p-4" data-testid="content-review-saved">
        <p className="text-sm font-semibold text-ink">Review: {reviewDecisionLabel(savedReview.decision)}</p>
        <p className="mt-1 text-sm text-slate-700">Reviewer: {savedReview.reviewed_by}</p>
        {savedReview.notes ? <p className="mt-2 text-sm leading-6 text-slate-700">Notatka: {savedReview.notes}</p> : null}
        <details className="mt-3 text-xs leading-5 text-slate-600"><summary className="cursor-pointer font-semibold text-slate-700">Dokładna wersja</summary><p className="mt-2 break-all">Rewizja: {savedReview.revision_id} · digest: {savedReview.revision_digest}</p></details>
        {savedReview.decision === "approved" && savedReview.revision_id === revision.revision_id && savedReview.revision_digest === revision.content_digest ? <ContentApprovedHtmlPackage workItemId={revision.work_item_id} revisionId={revision.revision_id} revisionDigest={revision.content_digest} /> : null}
        <button type="button" className="mt-3 rounded-md border border-action/30 px-3 py-2 text-sm font-semibold text-action" onClick={onReturnToText}>Wróć do tekstu</button>
      </div>
    );
  }
  if (!reviewAvailable) {
    return (
      <div className="mt-5 rounded-xl border border-wait/30 bg-wait/5 p-4" data-testid="content-review-context-blocker">
        <p className="text-sm font-semibold text-ink">Ta wersja nie jest już aktualna do review.</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">{revision.title} pozostaje dostępna do odczytu, ale WILQ wymaga świeżej rewizji powiązanej z aktualnym planem.</p>
        <button type="button" className="mt-3 rounded-md border border-action/30 px-3 py-2 text-sm font-semibold text-action" onClick={onReturnToText}>Wróć do tekstu</button>
      </div>
    );
  }
  if (conflict) {
    return (
      <div className="mt-5 rounded-xl border border-wait/30 bg-wait/5 p-4" data-testid="content-review-conflict">
        <p className="text-sm font-semibold text-ink">Wersja zmieniła się przed zapisem review.</p>
        <p className="mt-1 text-sm leading-6 text-slate-700">{conflict.safe_next_step}</p>
        <button type="button" className="mt-3 rounded-md border border-wait/40 px-3 py-2 text-sm font-semibold text-ink" onClick={onReloadCurrent}>Wczytaj aktualną wersję</button>
      </div>
    );
  }
  return (
    <div className="mt-5 rounded-xl border border-line bg-slate-50 p-4" data-testid="content-review-decision-panel">
      <p className="font-semibold text-ink">Sprawdź tekst</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">Jeśli tekst odpowiada materiałom i źródłom, zatwierdź tę wersję.</p>
      {!hasOperatorIdentity ? <p className="mt-2 text-sm font-semibold text-wait">Nie udało się potwierdzić tożsamości osoby oceniającej. Review nie zostanie zapisane.</p> : null}
      {decision === "needs_changes" ? (
        <label className="mt-4 block text-sm font-semibold text-ink">Notatka<textarea className="mt-2 min-h-24 w-full rounded-md border border-line bg-white p-3 text-sm font-normal text-ink" value={notes} onChange={(event) => onNotesChange(event.target.value)} placeholder="Wyjaśnij, co wymaga zmiany lub dlaczego odrzucasz wersję." /></label>
      ) : <p className="mt-3 text-sm leading-6 text-slate-700">Nie musisz przepisywać decyzji ani zaznaczać checklisty — kliknięcie zapisze review dokładnie tej wersji z jej dowodami.</p>}
      {error ? <p className="mt-3 text-sm font-semibold text-wait">Nie udało się zapisać review: {error.message}</p> : null}
      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" className="rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={!canSubmit} onClick={onSubmit}>{isPending ? "Zapisuję review…" : decision === "approved" ? "Zatwierdź tekst" : "Zapisz uwagi"}</button>
        {decision === "approved" ? <button type="button" className="text-sm font-semibold text-action underline" disabled={isPending} onClick={() => onDecisionChange("needs_changes")}>Tekst wymaga zmian</button> : <button type="button" className="text-sm font-semibold text-action underline" disabled={isPending} onClick={() => onDecisionChange("approved")}>Wróć do zatwierdzania</button>}
      </div>
      <details className="mt-3 text-xs leading-5 text-slate-600"><summary className="cursor-pointer font-semibold text-slate-700">Dokładna wersja</summary><p className="mt-2 break-all">Rewizja: {revision.revision_id} · digest: {revision.content_digest}</p></details>
    </div>
  );
}

function revisionEvidenceIds(revision: ContentDraftRevision) {
  return [...new Set([
    ...revision.sections.flatMap((section) => section.evidence_ids),
    ...revision.faq.flatMap((item) => item.evidence_ids),
    ...revision.cta_blocks.flatMap((item) => item.evidence_ids),
    ...revision.internal_links.flatMap((item) => item.evidence_ids)
  ])];
}

function reviewDecisionLabel(decision: ContentDraftRevisionDecision) {
  if (decision === "approved") return "Zatwierdzam";
  if (decision === "needs_changes") return "Wymaga zmian";
  return "Odrzucam";
}
