import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useState } from "react";

import {
  saveContentWorkItemDraftRevisionReview,
  type ContentDraftRevision,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionReviewRequest
} from "../lib/api";
import { type ContentWorkflowSnapshot } from "./contentWorkflowRuntime";
import { ContentDocumentWorkspaceCanvas } from "./ContentDocumentWorkspaceCanvas";
import { ContentFullPagePreview } from "./ContentFullPagePreview";
import { ContentApprovedHtmlPackage } from "./ContentApprovedHtmlPackage";
import { ContentEditorialIntegrityReport } from "./ContentEditorialIntegrityReport";
import { ContentWorkflowEntryPanel } from "./ContentWorkflowEntryPanel";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";
import {
  useContentWorkflowQueries,
  type ContentDecisionContextQuery,
  type ContentDocumentWorkspaceQuery,
  type ContentWorkflowEntryQuery,
  type ContentInitialDraftQuery,
  type ContentInventoryCatalogQuery,
  type ContentWorkflowSnapshotQuery
} from "./contentWorkflowQueries";

export function ContentWorkflowSurface() {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const selectedWorkItemId = stringFromSearch(routeSearch, "work_item_id");
  const reviewOpen = useRouterState({
    select: (state) => Reflect.get(state.location.search, "review") === 1
  });
  const browseInventory = useRouterState({
    select: (state) => Reflect.get(state.location.search, "browse") === 1
  });
  const newPageId = useRouterState({
    select: (state) => {
      const value = Reflect.get(state.location.search, "new_page");
      return typeof value === "string" && value ? value : null;
    }
  });
  const newPageOpen = Boolean(newPageId);
  const selectWorkItem = (workItemId: string) => {
    void navigate({
      to: "/content-workflow",
      search: (previous) => ({
        ...previous,
        work_item_id: workItemId,
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
    decisionContext,
    documentWorkspace,
    entry,
    inventory,
    operatorContext,
    workflow,
    initialDraft
  } = useContentWorkflowQueries(
    selectedWorkItemId,
    reviewOpen,
    browseInventory
  );

  return (
    <ContentWorkflowRouteState
      selectedWorkItemId={selectedWorkItemId}
      decisionContext={decisionContext}
      documentWorkspace={documentWorkspace}
      entry={entry}
      inventory={inventory}
      initialDraft={initialDraft}
      workflow={workflow}
      reviewOpen={reviewOpen}
      browseInventory={browseInventory}
      newPageOpen={newPageOpen}
      newPageId={newPageId}
      operatorLabel={operatorContext.data?.request_label ?? null}
      onSelectWorkItem={selectWorkItem}
      onBrowseInventory={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: 1, new_page: undefined })
        });
      }}
      onOpenNewPage={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: "1" })
        });
      }}
      onNewPageBriefSaved={(briefId) => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: briefId })
        });
      }}
      onCloseEntrySecondaryView={() => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({ ...contentWorkflowSearch(previous), browse: undefined, new_page: undefined })
        });
      }}
      onOpenReview={(workItemId) => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({
            work_item_id: workItemId,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: 1,
            review: 1,
            browse: undefined,
            new_page: undefined
          })
        });
      }}
      onReturnToText={(workItemId) => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({
            work_item_id: workItemId,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: 1,
            review: undefined,
            browse: undefined,
            new_page: undefined
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
}) {
  return {
    work_item_id: previous.work_item_id,
    section_heading: previous.section_heading,
    planning_digest: previous.planning_digest,
    workspace: previous.workspace,
    text: previous.text,
    review: previous.review,
    browse: previous.browse,
    new_page: previous.new_page
  };
}

function ContentWorkflowRouteState({
  selectedWorkItemId,
  decisionContext,
  documentWorkspace,
  entry,
  inventory,
  initialDraft,
  workflow,
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
  decisionContext: ContentDecisionContextQuery;
  documentWorkspace: ContentDocumentWorkspaceQuery;
  entry: ContentWorkflowEntryQuery;
  inventory: ContentInventoryCatalogQuery;
  initialDraft: ContentInitialDraftQuery;
  workflow: ContentWorkflowSnapshotQuery;
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
    if (entry.isLoading) return <ContentWorkflowEntryPending />;
    if (entry.error || !entry.data) {
      return <ContentWorkflowEntryFailure onRetry={() => void entry.refetch()} />;
    }
    return (
      <ContentWorkflowEntryPanel
        entry={entry.data}
        inventory={inventory.data ?? null}
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
        documentWorkspace={documentWorkspace}
        onOpenReview={onOpenReview}
      />
    );
  }
  return <ContentReviewRoute
    decisionContext={decisionContext}
    initialDraft={initialDraft}
    workflow={workflow}
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
  documentWorkspace,
  onOpenReview
}: {
  workItemId: string;
  documentWorkspace: ContentDocumentWorkspaceQuery;
  onOpenReview: (workItemId: string) => void;
}) {
  if (documentWorkspace.isLoading) {
    return <DocumentWorkspacePending />;
  }
  if (documentWorkspace.error || !documentWorkspace.data) {
    return <DocumentWorkspaceError onRetry={() => void documentWorkspace.refetch()} />;
  }
  const workspace = documentWorkspace.data;
  return <ContentDocumentWorkspaceCanvas workspace={workspace} onOpenReview={() => onOpenReview(workItemId)} />;
}

function DocumentWorkspacePending() {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-pending"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-line bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Wczytuję aktualną stronę…</p><p className="mt-2 text-sm text-slate-700">Pobieram materiał źródłowy i stan dokumentu. To nie jest błąd.</p></section></main>;
}

function DocumentWorkspaceError({ onRetry }: { onRetry: () => void }) {
  return <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-document-workspace-error"><ContentWorkflowWorkspaceHeader /><section className="mt-4 rounded-2xl border border-wait/30 bg-white p-5 shadow-sm"><p className="mt-2 text-lg font-semibold text-ink">Nie udało się odczytać workspace’u strony.</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={onRetry}>Spróbuj ponownie</button></section></main>;
}

function ContentReviewWorkspace({
  context,
  initialDraft,
  workflow,
  operatorLabel,
  onReturnToText
}: {
  context: NonNullable<ContentDecisionContextQuery["data"]>;
  initialDraft: ContentInitialDraftQuery;
  workflow: ContentWorkflowSnapshotQuery;
  operatorLabel: string | null;
  onReturnToText: (workItemId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState<ContentDraftRevisionDecision>("approved");
  const [notes, setNotes] = useState("");
  const [contentChecked, setContentChecked] = useState(false);
  const [evidenceChecked, setEvidenceChecked] = useState(false);
  const revision = initialDraft.data?.status === "created" ? initialDraft.data.revision ?? null : null;
  const completeRevision = revision?.page_assets ? revision : null;
  const persistedReview = workflow.data?.revisionWorkspace.latest_review;
  const matchingReview = persistedReview && completeRevision &&
    persistedReview.revision_id === completeRevision.revision_id &&
    persistedReview.revision_digest === completeRevision.content_digest
    ? persistedReview
    : null;
  const evidenceIds = completeRevision ? revisionEvidenceIds(completeRevision) : [];
  const reviewMutation = useMutation({
    mutationFn: (request: ContentDraftRevisionReviewRequest) =>
      saveContentWorkItemDraftRevisionReview(request, context.work_item_id, completeRevision!.revision_id),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["content-workflow", "work-item", context.work_item_id]
      });
    }
  });
  const canSubmit = Boolean(
    completeRevision &&
      operatorLabel &&
      !matchingReview &&
      !reviewMutation.isPending &&
      !workflow.error &&
      (decision === "approved"
        ? contentChecked && evidenceChecked && evidenceIds.length > 0
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
        ? ["Przeczytano dokładną treść tej wersji.", "Sprawdzono dowody przypisane do tej wersji."]
        : [],
      evidence_ids: decision === "approved" ? evidenceIds : []
    });
  };

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-review-workspace">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Review treści</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
          {context.source_public.title ?? "Wybrana strona"}
        </h1>
        {context.source_public.url ? <p className="mt-2 break-all text-sm text-action">{context.source_public.url}</p> : null}
        <p className="mt-2 text-sm font-medium text-slate-700">Usługa: {context.service.label ?? "niepotwierdzona"}</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">Wynik pracy: pełna rewizja HTML do review.</p>
        <ol className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-slate-600" aria-label="Stan pipeline’u">
          <li>Kontekst</li><li aria-hidden="true">→</li><li>Szkic</li><li aria-hidden="true">→</li><li className="text-action">Review</li><li aria-hidden="true">→</li><li>Odbiór opcjonalny</li>
        </ol>
      </section>
      <section className="mt-4 rounded-2xl border border-line bg-white p-4 shadow-sm lg:p-5">
        {completeRevision ? <ContentFullPagePreview revision={completeRevision} proposal={null} /> : (
          <div data-testid="content-review-blocker">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Stan review</p>
            <h2 className="mt-2 text-lg font-semibold text-ink">Pełna rewizja HTML — niegotowa do review</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">
              {initialDraft.data?.blockers[0]?.reason ?? initialDraft.data?.safe_next_step ?? "Brakuje kompletnej exact revision."}
            </p>
          </div>
        )}
        {completeRevision ? (
          <><ReviewDecisionPanel
            revision={completeRevision}
            matchingReview={matchingReview}
            isLoadingPersistedState={workflow.isLoading}
            persistedStateError={workflow.error}
            hasOperatorIdentity={Boolean(operatorLabel)}
            decision={decision}
            notes={notes}
            contentChecked={contentChecked}
            evidenceChecked={evidenceChecked}
            canSubmit={canSubmit}
            isPending={reviewMutation.isPending}
            error={reviewMutation.error}
            result={reviewMutation.data}
            onDecisionChange={setDecision}
            onNotesChange={setNotes}
            onContentCheckedChange={setContentChecked}
            onEvidenceCheckedChange={setEvidenceChecked}
            onSubmit={submitReview}
            onReloadCurrent={() => {
              void Promise.all([
                queryClient.invalidateQueries({ queryKey: ["content-workflow", "work-item", context.work_item_id, "initial-draft"] }),
                queryClient.invalidateQueries({ queryKey: ["content-workflow", "work-item", context.work_item_id] })
              ]);
            }}
            onReturnToText={() => onReturnToText(context.work_item_id)}
          />{completeRevision.base_revision_id ? <ContentEditorialIntegrityReport workItemId={context.work_item_id} revisionId={completeRevision.revision_id} /> : null}</>
        ) : null}
      </section>
      <details className="mt-4 rounded-xl border border-line bg-white p-4 text-sm text-slate-700">
        <summary className="cursor-pointer font-semibold text-ink">Szczegóły, źródła i ograniczenia</summary>
        <p className="mt-3 leading-6">{context.delivery_capability.reason}</p>
      </details>
    </main>
  );
}

function ContentReviewRoute({
  decisionContext,
  initialDraft,
  workflow,
  operatorLabel,
  onReturnToText
}: {
  decisionContext: ContentDecisionContextQuery;
  initialDraft: ContentInitialDraftQuery;
  workflow: ContentWorkflowSnapshotQuery;
  operatorLabel: string | null;
  onReturnToText: (workItemId: string) => void;
}) {
  if (decisionContext.isLoading || initialDraft.isLoading || workflow.isLoading) {
    return <DocumentWorkspacePending />;
  }
  if (decisionContext.error || !decisionContext.data || initialDraft.error) {
    return <DocumentWorkspaceError onRetry={() => {
      void Promise.all([decisionContext.refetch(), initialDraft.refetch(), workflow.refetch()]);
    }} />;
  }
  return <ContentReviewWorkspace
    context={decisionContext.data}
    initialDraft={initialDraft}
    workflow={workflow}
    operatorLabel={operatorLabel}
    onReturnToText={onReturnToText}
  />;
}

function ReviewDecisionPanel({
  revision,
  matchingReview,
  isLoadingPersistedState,
  persistedStateError,
  hasOperatorIdentity,
  decision,
  notes,
  contentChecked,
  evidenceChecked,
  canSubmit,
  isPending,
  error,
  result,
  onDecisionChange,
  onNotesChange,
  onContentCheckedChange,
  onEvidenceCheckedChange,
  onSubmit,
  onReloadCurrent,
  onReturnToText
}: {
  revision: ContentDraftRevision;
  matchingReview: ContentWorkflowSnapshot["revisionWorkspace"]["latest_review"];
  isLoadingPersistedState: boolean;
  persistedStateError: Error | null;
  hasOperatorIdentity: boolean;
  decision: ContentDraftRevisionDecision;
  notes: string;
  contentChecked: boolean;
  evidenceChecked: boolean;
  canSubmit: boolean;
  isPending: boolean;
  error: Error | null;
  result: Awaited<ReturnType<typeof saveContentWorkItemDraftRevisionReview>> | undefined;
  onDecisionChange: (decision: ContentDraftRevisionDecision) => void;
  onNotesChange: (notes: string) => void;
  onContentCheckedChange: (checked: boolean) => void;
  onEvidenceCheckedChange: (checked: boolean) => void;
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
        <p className="mt-1 text-sm text-slate-700">Rewizja: {savedReview.revision_id.slice(0, 12)} · {savedReview.revision_digest.slice(0, 12)}</p>
        <p className="mt-1 text-sm text-slate-700">Reviewer: {savedReview.reviewed_by}</p>
        {savedReview.notes ? <p className="mt-2 text-sm leading-6 text-slate-700">Notatka: {savedReview.notes}</p> : null}
        {savedReview.decision === "approved" && savedReview.revision_id === revision.revision_id && savedReview.revision_digest === revision.content_digest ? <ContentApprovedHtmlPackage workItemId={revision.work_item_id} revisionId={revision.revision_id} revisionDigest={revision.content_digest} /> : null}
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
      <p className="font-semibold text-ink">Decyzja człowieka</p>
      <p className="mt-1 text-sm leading-6 text-slate-700">Rewizja: {revision.revision_id.slice(0, 12)} · digest: {revision.content_digest.slice(0, 12)}</p>
      {isLoadingPersistedState ? <p className="mt-2 text-sm text-slate-600">Sprawdzam zapisany stan review…</p> : null}
      {persistedStateError ? <p className="mt-2 text-sm font-semibold text-wait">Nie udało się odczytać aktualnego stanu review. Odśwież stronę przed zapisem decyzji.</p> : null}
      {!hasOperatorIdentity ? <p className="mt-2 text-sm font-semibold text-wait">Nie udało się potwierdzić tożsamości osoby oceniającej. Review nie zostanie zapisane.</p> : null}
      <fieldset className="mt-4 flex flex-wrap gap-2" disabled={isPending || isLoadingPersistedState || Boolean(persistedStateError) || !hasOperatorIdentity}>
        {(["approved", "needs_changes", "rejected"] as const).map((option) => (
          <label key={option} className={`cursor-pointer rounded-md border px-3 py-2 text-sm font-semibold ${decision === option ? "border-action bg-action/10 text-action" : "border-line bg-white text-ink"}`}>
            <input className="sr-only" type="radio" name="content-review-decision" value={option} checked={decision === option} onChange={() => onDecisionChange(option)} />
            {reviewDecisionLabel(option)}
          </label>
        ))}
      </fieldset>
      {decision === "approved" ? (
        <div className="mt-4 space-y-2 text-sm text-slate-700">
          <label className="flex gap-2"><input type="checkbox" checked={contentChecked} onChange={(event) => onContentCheckedChange(event.target.checked)} />Przeczytano dokładną treść tej wersji.</label>
          <label className="flex gap-2"><input type="checkbox" checked={evidenceChecked} onChange={(event) => onEvidenceCheckedChange(event.target.checked)} />Sprawdzono dowody przypisane do tej wersji.</label>
        </div>
      ) : (
        <label className="mt-4 block text-sm font-semibold text-ink">Notatka<textarea className="mt-2 min-h-24 w-full rounded-md border border-line bg-white p-3 text-sm font-normal text-ink" value={notes} onChange={(event) => onNotesChange(event.target.value)} placeholder="Wyjaśnij, co wymaga zmiany lub dlaczego odrzucasz wersję." /></label>
      )}
      {error ? <p className="mt-3 text-sm font-semibold text-wait">Nie udało się zapisać review: {error.message}</p> : null}
      <button type="button" className="mt-4 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={!canSubmit} onClick={onSubmit}>{isPending ? "Zapisuję review…" : "Zapisz review"}</button>
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
