import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  postContentWorkItemCodexSectionProposal,
  getContentWorkItemInitialDraft,
  postContentWorkItemInitialDraft,
  postContentWorkItemSemanticReview,
  postContentWorkItemWordPressAuthoringPayloadPreview,
  postContentWorkItemWordPressDraftExecution,
  getContentInventoryMaterial,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview,
  saveContentWorkItemPlanningReview,
  type ContentDraftRevision,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionReviewRequest,
  type ContentDraftRevisionSaveRequest,
  type ContentDraftRevisionSection,
  type ContentInventoryCatalogResponse,
  type ContentPlanningReviewRequest,
  type ContentSemanticReviewResponse,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentOpportunityEnrichment,
  type WordPressAuthoringProfile,
  type ContentInventoryMaterialResponse
} from "../lib/api";
import { marketerWorkflowStepTitle, type ContentWorkflowSnapshot, type WorkflowStepId } from "./contentWorkflowRuntime";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { ContentInventoryCatalogPanel } from "./ContentInventoryCatalogPanel";
import {
  ContentWorkflowError,
  ContentWorkflowSelectedLoading,
  ContentWorkflowInventorySelectionLoading,
  type ContentSourceRefreshControl
} from "./ContentWorkflowBoundaryStates";
import { ContentWorkflowBlockedCandidate } from "./ContentWorkflowBlockedCandidate";
import { ContentDecisionContextPanel } from "./ContentDecisionContextPanel";
import { ContentFullPagePreview } from "./ContentFullPagePreview";
import { ContentApprovedHtmlPackage } from "./ContentApprovedHtmlPackage";
import { ContentEditorialIntegrityReport } from "./ContentEditorialIntegrityReport";
import { ContentPageWorkbench as ContentPageWorkbenchView } from "./ContentPageWorkbench";
import { ContentWorkflowJourneyContext } from "./ContentWorkflowJourneyContext";
import { ContentWorkflowTaskMap } from "./ContentWorkflowTaskMap";
import { ContentWorkflowSourcesView } from "./ContentWorkflowSourcesView";
import { ContentKnowledgeReadinessNotice } from "./ContentKnowledgeReadinessNotice";
import { ContentWorkflowWorkspaceHeader } from "./ContentWorkflowWorkspaceHeader";
import {
  acfPreviewResultFrom,
  acfPreviewRequest,
  executionResultFrom,
  submitIfReady,
  wordpressExecutionRequest
} from "./contentWorkflowActionModel";
import {
  useContentWorkflowQueries,
  type ContentOpportunityEnrichmentQuery,
  type ContentDecisionContextQuery,
  type ContentInitialDraftQuery,
  type ContentOperatorContextQuery,
  type ContentWorkItemQueueQuery,
  type ContentInventoryCatalogQuery,
  type ContentServiceProfileQuery,
  type ContentWorkflowSnapshotQuery,
  type KnowledgeSourceMaterialsQuery,
  type KnowledgeSourceMaterialReadinessQuery,
  type WordPressAuthoringProfileQuery,
  type WordPressDraftActivationPacketQuery,
  type ContentWorkItemQueueCandidate
} from "./contentWorkflowQueries";

type ContentWorkflowActions = ReturnType<typeof useContentWorkflowActions>;
type ContentWorkflowMutations = ReturnType<typeof useContentWorkflowMutations>;
type CodexProposalMutationInput = {
  baseRevision: ContentDraftRevision;
  selection: { sectionIds: string[] } | { sectionHeadings: string[] };
};
type InitialDraftMutationInput = NonNullable<
  ContentWorkflowSnapshot["planningWorkspace"]
>["proposal"];
export function ContentWorkflowSurface() {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const sourceRefresh = useContentSourceRefresh();
  const selectedWorkItemId = stringFromSearch(routeSearch, "work_item_id");
  const textWorkspaceOpen = useRouterState({
    select: (state) => Reflect.get(state.location.search, "text") === "1"
  });
  const reviewOpen = useRouterState({
    select: (state) => Reflect.get(state.location.search, "review") === "1"
  });
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
        review: undefined
      })
    });
  };
  const {
    activeWorkItemId,
    authoringProfile,
    draftActivationPacket,
    decisionContext,
    enrichment,
    inventory,
    knowledgeMaterials,
    knowledgeReadiness,
    operatorContext,
    serviceProfile,
    queue,
    selectedCandidate,
    workflow,
    initialDraft
  } = useContentWorkflowQueries(selectedWorkItemId, textWorkspaceOpen, reviewOpen);

  return (
    <ContentWorkflowRouteState
      activeWorkItemId={activeWorkItemId}
      selectedWorkItemId={selectedWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      decisionContext={decisionContext}
      enrichment={enrichment}
      inventory={inventory}
      initialDraft={initialDraft}
      knowledgeMaterials={knowledgeMaterials}
      knowledgeReadiness={knowledgeReadiness}
      operatorContext={operatorContext}
      serviceProfile={serviceProfile}
      queue={queue}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      textWorkspaceOpen={textWorkspaceOpen}
      reviewOpen={reviewOpen}
      operatorLabel={operatorContext.data?.request_label ?? null}
      sourceRefresh={sourceRefresh}
      onSelectWorkItem={selectWorkItem}
      onOpenTextWorkspace={(workItemId) => {
        void navigate({
          to: "/content-workflow",
          search: (previous) => ({
            work_item_id: workItemId,
            section_heading: previous.section_heading,
            planning_digest: previous.planning_digest,
            workspace: undefined,
            text: "1",
            review: undefined
          })
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
            text: "1",
            review: "1"
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
            text: "1",
            review: undefined
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

function useContentSourceRefresh(): ContentSourceRefreshControl {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ContentSourceRefreshControl["status"]>("idle");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);
  const refreshMutation = useMutation({
    mutationFn: (url: string) => getContentInventoryMaterial(url),
    onMutate: () => {
      setStatus("loading");
      setSummary("");
      setError(null);
    },
    onSuccess: (result: ContentInventoryMaterialResponse) => {
      if (result.status === "ready") {
        setStatus("success");
        setSummary("Strona została odczytana ponownie.");
      } else {
        setStatus("error");
        setError(result.blocker ?? "Nie udało się odczytać tej strony.");
      }
      void queryClient.invalidateQueries({ queryKey: ["content-workflow"] });
    },
    onError: (reason) => {
      setStatus("error");
      setError(reason instanceof Error ? reason.message : "Nie udało się odczytać tej strony.");
    }
  });
  return {
    active: refreshMutation.isPending,
    status,
    summary,
    error,
    onRefresh: (url) => {
      if (!refreshMutation.isPending) refreshMutation.mutate(url);
    }
  };
}

function ContentWorkflowRouteState({
  activeWorkItemId,
  selectedWorkItemId,
  authoringProfile,
  draftActivationPacket,
  decisionContext,
  enrichment,
  inventory,
  initialDraft,
  knowledgeMaterials,
  knowledgeReadiness,
  operatorContext,
  serviceProfile,
  queue,
  selectedCandidate,
  workflow,
  textWorkspaceOpen,
  reviewOpen,
  operatorLabel,
  sourceRefresh,
  onSelectWorkItem,
  onOpenTextWorkspace,
  onOpenReview,
  onReturnToText
}: {
  activeWorkItemId: string | null;
  selectedWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  decisionContext: ContentDecisionContextQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  inventory: ContentInventoryCatalogQuery;
  initialDraft: ContentInitialDraftQuery;
  knowledgeMaterials: KnowledgeSourceMaterialsQuery;
  knowledgeReadiness: KnowledgeSourceMaterialReadinessQuery;
  operatorContext: ContentOperatorContextQuery;
  serviceProfile: ContentServiceProfileQuery;
  queue: ContentWorkItemQueueQuery;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  textWorkspaceOpen: boolean;
  reviewOpen: boolean;
  operatorLabel: string | null;
  sourceRefresh: ContentSourceRefreshControl;
  onSelectWorkItem: (workItemId: string) => void;
  onOpenTextWorkspace: (workItemId: string) => void;
  onOpenReview: (workItemId: string) => void;
  onReturnToText: (workItemId: string) => void;
}) {
  if (queue.isLoading) {
    const selectedInventoryItem = selectedWorkItemId
      ? inventory.data?.items.find((item) => item.work_item_id === selectedWorkItemId)
      : undefined;
    return selectedInventoryItem ? <ContentWorkflowInventorySelectionLoading item={selectedInventoryItem} /> : <LoadingBand />;
  }
  if (queue.error || !queue.data) return <ContentWorkflowError />;
  return (
    <ContentWorkflowQueueReady
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      decisionContext={decisionContext}
      enrichment={enrichment}
      inventory={inventory}
      initialDraft={initialDraft}
      knowledgeMaterials={knowledgeMaterials}
      knowledgeReadiness={knowledgeReadiness}
      operatorContext={operatorContext}
      serviceProfile={serviceProfile}
      queue={queue.data}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      textWorkspaceOpen={textWorkspaceOpen}
      reviewOpen={reviewOpen}
      operatorLabel={operatorLabel}
      sourceRefresh={sourceRefresh}
      onSelectWorkItem={onSelectWorkItem}
      onOpenTextWorkspace={onOpenTextWorkspace}
      onOpenReview={onOpenReview}
      onReturnToText={onReturnToText}
    />
  );
}

function ContentWorkflowQueueReady({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  decisionContext,
  enrichment,
  inventory,
  initialDraft,
  knowledgeMaterials,
  knowledgeReadiness,
  operatorContext,
  serviceProfile,
  queue,
  selectedCandidate,
  workflow,
  textWorkspaceOpen,
  reviewOpen,
  operatorLabel,
  sourceRefresh,
  onSelectWorkItem,
  onOpenTextWorkspace,
  onOpenReview,
  onReturnToText
}: {
  activeWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  decisionContext: ContentDecisionContextQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  inventory: ContentInventoryCatalogQuery;
  initialDraft: ContentInitialDraftQuery;
  knowledgeMaterials: KnowledgeSourceMaterialsQuery;
  knowledgeReadiness: KnowledgeSourceMaterialReadinessQuery;
  operatorContext: ContentOperatorContextQuery;
  serviceProfile: ContentServiceProfileQuery;
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  textWorkspaceOpen: boolean;
  reviewOpen: boolean;
  operatorLabel: string | null;
  sourceRefresh: ContentSourceRefreshControl;
  onSelectWorkItem: (workItemId: string) => void;
  onOpenTextWorkspace: (workItemId: string) => void;
  onOpenReview: (workItemId: string) => void;
  onReturnToText: (workItemId: string) => void;
}) {
  if (!activeWorkItemId) {
    return (
      <main className="min-h-screen w-full bg-[radial-gradient(circle_at_top_right,_#e7f5f1,_transparent_38%),linear-gradient(180deg,_#f8fbfa_0%,_#ffffff_48%)] px-4 py-5 lg:px-7 2xl:px-8">
        <div className="mb-6 overflow-hidden rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-[0_18px_50px_-30px_rgba(15,118,110,0.45)] backdrop-blur lg:p-7">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div className="max-w-2xl">
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-action">Treści i SEO · centrum decyzji</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink lg:text-4xl">Tworzenie i odświeżanie treści</h1>
              <p className="mt-3 text-sm leading-7 text-slate-600 lg:text-base">
                Najpierw zobaczysz materiał źródłowy i jego metryki. Dopiero potem WILQ pokaże dopasowane usługi, plan i bezpieczny następny krok.
              </p>
            </div>
            <div className="grid min-w-[15rem] grid-cols-2 gap-2 text-xs">
              <OverviewMetric label="adresów" value={inventory.data?.total_count ?? 0} />
              <OverviewMetric label="z materiałem" value={(inventory.data?.ready_count ?? 0) + (inventory.data?.partial_count ?? 0)} accent />
              <OverviewMetric label="z metrykami" value={inventory.data ? inventory.data.items.filter((item) => item.metrics_status === "available").length : 0} />
              <OverviewMetric label="do sprawdzenia" value={inventory.data?.blocked_count ?? 0} muted />
            </div>
          </div>
          <ContentKnowledgeReadinessNotice query={knowledgeReadiness} materials={knowledgeMaterials} />
          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-4 text-xs text-slate-500">
            <span className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1.5 font-semibold text-emerald-700"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />Dane read-only</span>
            <span>WordPress · GSC/GA4 · karty wiedzy</span>
            <span className="ml-auto">Nie ma automatycznego wyboru ani publikacji</span>
          </div>
        </div>
        <ContentCandidateQueuePanel
          queue={queue}
          inventory={inventory.data ?? null}
          selectedWorkItemId=""
          onSelectWorkItem={onSelectWorkItem}
        />
        {inventory.isLoading ? <LoadingBand /> : inventory.data ? <ContentInventoryCatalogPanel catalog={inventory.data} queue={queue} serviceProfile={serviceProfile.data ?? null} onSelectWorkItem={onSelectWorkItem} /> : null}
      </main>
    );
  }
  if (textWorkspaceOpen && activeWorkItemId && decisionContext.data) {
    return reviewOpen
      ? <ContentReviewWorkspace
          context={decisionContext.data}
          initialDraft={initialDraft}
          workflow={workflow}
          operatorLabel={operatorLabel}
          onReturnToText={onReturnToText}
        />
      : <ContentTextWorkspace context={decisionContext.data} initialDraft={initialDraft} onOpenReview={onOpenReview} />;
  }
  if (decisionContext.data && selectedCandidate?.source_public_url) {
    return <ContentDecisionContextPanel context={decisionContext.data} onOpenTextWorkspace={onOpenTextWorkspace} />;
  }
  if (selectedCandidate?.recommended_mode === "block" && selectedCandidate.source_public_url) {
    if (decisionContext.isLoading) {
      return <ContentWorkflowSelectedLoading candidate={selectedCandidate} />;
    }
    if (decisionContext.error || !decisionContext.data) {
      return <ContentWorkflowSelectedLoading candidate={selectedCandidate} error />;
    }
    return <ContentDecisionContextPanel context={decisionContext.data} onOpenTextWorkspace={onOpenTextWorkspace} />;
  }
  if (selectedCandidate?.recommended_mode === "block") {
    return (
      <ContentWorkflowBlockedCandidate
        queue={queue}
        selectedCandidate={selectedCandidate}
        selectedWorkItemId={activeWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
        refresh={sourceRefresh}
      />
    );
  }
  return (
      <ContentWorkflowSelectedReady
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      operatorLabel={operatorContext.data?.request_label ?? "operator_local_dashboard"}
      draftActivationPacket={draftActivationPacket}
      enrichment={enrichment}
        queue={queue}
        inventory={inventory.data ?? null}
        selectedCandidate={selectedCandidate}
        workflow={workflow}
        onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function OverviewMetric({ label, value, accent = false, muted = false }: { label: string; value: number; accent?: boolean; muted?: boolean }) {
  return <div className={`rounded-xl border px-3 py-3 ${accent ? "border-action/20 bg-action/5" : muted ? "border-slate-200 bg-slate-50" : "border-slate-100 bg-white"}`}><div className={`text-2xl font-semibold ${accent ? "text-action" : muted ? "text-slate-500" : "text-ink"}`}>{value.toLocaleString("pl-PL")}</div><div className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div></div>;
}

function ContentTextWorkspace({
  context,
  initialDraft,
  onOpenReview
}: {
  context: NonNullable<ContentDecisionContextQuery["data"]>;
  initialDraft: ContentInitialDraftQuery;
  onOpenReview: (workItemId: string) => void;
}) {
  const revision = initialDraft.data?.status === "created" ? initialDraft.data.revision ?? null : null;
  const completeRevision = revision?.page_assets ? revision : null;
  const blocker = initialDraft.data?.blockers[0] ?? null;

  return (
    <main className="mx-auto max-w-7xl px-4 py-5 lg:px-8" data-testid="content-text-workspace">
      <ContentWorkflowWorkspaceHeader />
      <section className="rounded-2xl border border-action/25 bg-white p-5 shadow-sm lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-action">Tekst strony</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-ink lg:text-3xl">
          {context.source_public.title ?? "Wybrana strona"}
        </h1>
        {context.source_public.url ? <p className="mt-2 break-all text-sm text-action">{context.source_public.url}</p> : null}
        <p className="mt-2 text-sm font-medium text-slate-700">Usługa: {context.service.label ?? "niepotwierdzona"}</p>
        <p className="mt-3 text-sm leading-6 text-slate-700">Wynik pracy: pełna rewizja HTML do review.</p>
        <ol className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-semibold text-slate-600" aria-label="Stan pipeline’u">
          <li>Kontekst</li><li aria-hidden="true">→</li><li className="text-action">Szkic</li><li aria-hidden="true">→</li><li>Review</li><li aria-hidden="true">→</li><li>Odbiór opcjonalny</li>
        </ol>
      </section>
      <section className="mt-4 rounded-2xl border border-line bg-white p-4 shadow-sm lg:p-5">
        {initialDraft.isLoading ? <p className="text-sm text-slate-700">Wczytuję stan pełnego draftu HTML…</p> : null}
        {initialDraft.error ? <p className="text-sm font-semibold text-wait">Nie udało się odczytać stanu pełnego draftu HTML.</p> : null}
        {completeRevision ? <><ContentFullPagePreview revision={completeRevision} proposal={null} /><div className="mt-4 rounded-xl border border-action/20 bg-action/5 p-4"><p className="text-sm font-semibold text-ink">Pełna rewizja HTML</p><p className="mt-1 text-sm text-slate-700">Rewizja: {completeRevision.revision_id.slice(0, 12)} · stan: nieprzejrzana</p><button type="button" className="mt-3 rounded-md bg-action px-3 py-2 text-sm font-semibold text-white" onClick={() => onOpenReview(context.work_item_id)}>Przejdź do review</button></div>{completeRevision.base_revision_id ? <ContentEditorialIntegrityReport workItemId={context.work_item_id} revisionId={completeRevision.revision_id} /> : null}</> : !initialDraft.isLoading && !initialDraft.error ? (
          <div data-testid="content-text-workspace-blocker">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-wait">Stan tekstu</p>
            <h2 className="mt-2 text-lg font-semibold text-ink">Pełny draft HTML — niegotowy</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">{blocker?.reason ?? initialDraft.data?.safe_next_step ?? "WILQ nie ma kompletnej exact revision do pokazania."}</p>
            {blocker ? <p className="mt-3 text-sm font-semibold text-slate-700">{blocker.next_step}</p> : null}
          </div>
        ) : null}
      </section>
      <details className="mt-4 rounded-xl border border-line bg-white p-4 text-sm text-slate-700">
        <summary className="cursor-pointer font-semibold text-ink">Szczegóły, źródła i ograniczenia</summary>
        <p className="mt-3 leading-6">{context.delivery_capability.reason}</p>
      </details>
    </main>
  );
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

function ContentWorkflowSelectedReady({
  activeWorkItemId,
  authoringProfile,
  operatorLabel,
  draftActivationPacket,
  enrichment,
  queue,
  inventory,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string;
  authoringProfile: WordPressAuthoringProfileQuery;
  operatorLabel: string;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  inventory: ContentInventoryCatalogResponse | null;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (selectedCandidate === null) return <ContentWorkflowError />;
  if (workflow.isLoading) {
    return (
      <ContentWorkflowSelectedLoading
        candidate={selectedCandidate}
      />
    );
  }
  if (workflow.error || !workflow.data) {
    return (
      <ContentWorkflowSelectedLoading
        candidate={selectedCandidate}
        error
      />
    );
  }
  return (
    <ContentWorkflowLoaded
      key={activeWorkItemId}
      data={workflow.data}
      authoringProfile={authoringProfile}
      operatorLabel={operatorLabel}
      draftActivationPacket={draftActivationPacket}
      enrichment={enrichment.data?.enrichment ?? null}
      queue={queue}
      inventory={inventory}
      selectedWorkItemId={activeWorkItemId}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowLoaded({
  data,
  authoringProfile,
  operatorLabel,
  draftActivationPacket,
  enrichment,
  queue,
  inventory,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  data: ContentWorkflowSnapshot;
  authoringProfile: WordPressAuthoringProfileQuery;
  operatorLabel: string;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  inventory: ContentInventoryCatalogResponse | null;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const actions = useContentWorkflowActions(
    data,
    selectedWorkItemId,
    authoringProfile.data ?? null,
    operatorLabel
  );
  const [viewMode, setViewMode] = useState<"marketer" | "technical">("marketer");
  return (
    <main className="w-full px-4 py-3 sm:py-5 lg:px-7 2xl:px-8">
      {viewMode === "technical" ? (
        <ContentWorkflowWorkspaceHeader>
          <span className="sr-only">Metryki, źródła i szczegóły do sprawdzenia przed przekazaniem.</span>
          <div className="flex rounded-md border border-line bg-white p-1 shadow-sm" role="group" aria-label="Tryb widoku">
            <button
              type="button"
              aria-label="Wróć do treści i SEO"
              onClick={() => setViewMode("marketer")}
              className="rounded px-3 py-2 text-sm font-semibold text-slate-600"
            >
              Wróć do treści i SEO
            </button>
          </div>
        </ContentWorkflowWorkspaceHeader>
      ) : (
        <div className="hidden lg:block">
          <ContentWorkflowWorkspaceHeader />
        </div>
      )}

      {viewMode === "marketer" ? (
          <ContentWorkflowMarketerJourney
          key={`${selectedWorkItemId}:${data.currentStepId}`}
          actions={actions}
          authoringProfile={authoringProfile}
          data={data}
          draftActivationPacket={draftActivationPacket}
          enrichment={enrichment}
          queue={queue}
          inventory={inventory}
          selectedWorkItemId={selectedWorkItemId}
          onSelectWorkItem={onSelectWorkItem}
          onShowSources={() => setViewMode("technical")}
        />
      ) : (
        <ContentWorkflowSourcesView data={data} />
      )}
    </main>
  );
}

function ContentWorkflowMarketerJourney({
  actions,
  authoringProfile,
  data,
  draftActivationPacket,
  enrichment,
  queue,
  inventory,
  selectedWorkItemId,
  onSelectWorkItem,
  onShowSources
}: {
  actions: ContentWorkflowActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  inventory: ContentInventoryCatalogResponse | null;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
  onShowSources: () => void;
}) {
  const sectionMapCurrent = data.planningWorkspace?.section_map_current ?? false;
  const [selectedStepId, setSelectedStepId] = useState<WorkflowStepId>(
    sectionMapCurrent
      ? "draft"
      : data.currentStepId === "section_map"
        ? "scope"
        : data.currentStepId
  );
  const visibleSelectedStepId = sectionMapCurrent && (selectedStepId === "scope" || selectedStepId === "section_map")
    ? "draft"
    : !sectionMapCurrent && data.currentStepId === "section_map" && selectedStepId === "draft"
      ? "scope"
      : selectedStepId;
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const initialSectionHeading = stringFromSearch(routeSearch, "section_heading");
  const selectStep = (stepId: WorkflowStepId) => {
    const marketerStepId = stepId === "section_map"
      ? sectionMapCurrent
        ? "draft"
        : "scope"
      : stepId;
    if (data.operatorSteps.some((step) => step.id === marketerStepId && step.canOpen)) {
      setSelectedStepId(marketerStepId);
    }
  };

  return (
    <div data-testid="content-workflow-marketer-journey">
      <ContentSessionPicker
        workflowStatusLabel={marketerWorkflowStatusLabel(data)}
        queue={queue}
        inventory={inventory}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
        serviceLabel={data.serviceProfileContext.service_label ?? "Nieprzypisana usługa"}
        pageTitle={data.preflight.item.wordpress_title_or_h1 ?? data.candidate.title}
        pageUrl={data.preflight.item.source_public_url ?? data.preflight.item.final_canonical_url ?? data.preflight.item.intended_final_url}
      />
      <ContentNextStepHero
        step={data.operatorSteps.find((step) => step.id === visibleSelectedStepId) ?? data.operatorSteps[0]}
        nextStep={data.operatorSteps[data.operatorSteps.findIndex((step) => step.id === visibleSelectedStepId) + 1]}
        onAdvance={selectStep}
        onFocusCurrentStep={() => focusWorkflowStep(visibleSelectedStepId)}
        onFocusPlan={() => focusWorkflowStep("section_map")}
        sectionMapCurrent={sectionMapCurrent}
        planningCurrent={visibleSelectedStepId === "scope" ? data.planningWorkspace?.scope_current ?? true : visibleSelectedStepId === "section_map" ? sectionMapCurrent : true}
        fullDraftReady={Boolean(data.revisionWorkspace.latest_revision?.page_assets)}
      />
      <div className="flex flex-col">
        <div className="order-1">
          <ContentWorkflowJourneyContext data={data} onShowSources={onShowSources} />
        </div>
        <div className="order-2">
          <ContentWorkflowTaskMap
            currentStepId={sectionMapCurrent ? "draft" : data.currentStepId}
            selectedStepId={visibleSelectedStepId}
            steps={data.operatorSteps}
            sectionMapCurrent={sectionMapCurrent}
            onSelectStep={selectStep}
          />
        </div>
      </div>
      <ContentPageWorkbenchView
        actions={actions}
        authoringProfile={authoringProfile}
        data={data}
        draftActivationPacket={draftActivationPacket}
        enrichment={enrichment}
        activeStepId={visibleSelectedStepId}
        initialSectionHeading={initialSectionHeading ?? undefined}
      />
    </div>
  );
}

function marketerWorkflowStatusLabel(data: ContentWorkflowSnapshot): string {
  const current = data.operatorSteps.find((step) => step.id === data.currentStepId);
  if (!current) return "wymaga sprawdzenia";
  if (current.id === "dev_draft" && current.readiness === "ready") {
    return "gotowy szkic na devie";
  }
  if (current.id === "review" && current.readiness === "ready") {
    return "gotowa wersja do review";
  }
  if (current.id === "draft" && current.readiness === "ready") {
    return "gotowy tekst do sprawdzenia";
  }
  return current.statusLabel;
}

function ContentNextStepHero({
  step,
  nextStep,
  onAdvance,
  onFocusCurrentStep,
  onFocusPlan,
  sectionMapCurrent,
  planningCurrent,
  fullDraftReady
}: {
  step: ContentWorkflowSnapshot["operatorSteps"][number] | undefined;
  nextStep: ContentWorkflowSnapshot["operatorSteps"][number] | undefined;
  onAdvance: (stepId: WorkflowStepId) => void;
  onFocusCurrentStep: () => void;
  onFocusPlan: () => void;
  sectionMapCurrent: boolean;
  planningCurrent: boolean;
  fullDraftReady: boolean;
}) {
  if (!step) return null;
  const generatedTextReady = sectionMapCurrent && (step.id === "scope" || step.id === "draft");
  const effectivePlanningCurrent = planningCurrent || generatedTextReady;
  const planNeedsRefresh = effectivePlanningCurrent && step.id === "scope" && nextStep?.id === "section_map" && !sectionMapCurrent;
  const canAdvance = Boolean(nextStep?.canOpen) && !planNeedsRefresh;
  const nextStepLabel = nextStep?.id === "section_map" || nextStep?.id === "draft" ? "Przejdź do tekstu" : nextStep?.id === "review" ? "Przejdź do review" : nextStep?.id === "dev_draft" ? "Przejdź do odbioru" : "Zobacz kolejny krok";
  const currentStepLabel = workflowStepActionLabel(step.id, Boolean(step.blocker));
  const actionLabel = planNeedsRefresh
    ? "Otwórz kontekst planu"
    : canAdvance
      ? nextStepLabel
      : !effectivePlanningCurrent
        ? "Sprawdź aktualny zakres"
        : step.id === "draft" && !fullDraftReady
          ? "Sprawdź stan draftu"
        : currentStepLabel;
  const instruction = planNeedsRefresh
    ? "Zakres jest zapisany. Zbuduj plan z aktualnych danych, aby otworzyć tekst."
    : generatedTextReady
    ? workflowStepInstruction("draft")
    : !effectivePlanningCurrent
    ? "Poprzednia decyzja jest nieaktualna, bo zmienił się plan lub dowody. Sprawdź zakres jeszcze raz i zapisz aktualną decyzję."
    : step.id === "draft" && !fullDraftReady
    ? "Pełna rewizja HTML nie jest jeszcze gotowa; sprawdź blokadę zamiast otwierać edytor."
    : nextStep?.canOpen
      ? step.safeNextStep
    : workflowStepInstruction(step.id, step.blocker);
  return (
    <section className="wilq-enter wilq-enter-delay-1 mb-3 rounded-md border border-action/30 bg-action/5 px-3 py-3 shadow-sm sm:mb-4 sm:px-4" data-testid="content-next-step-hero">
      <div className="grid gap-3 lg:grid-cols-[minmax(13rem,0.8fr)_minmax(0,1.5fr)_auto] lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-action">Wynik pracy</p>
          <p className="mt-1 text-base font-semibold text-ink">Wersja robocza HTML do review</p>
          <p className="mt-1 text-xs leading-5 text-slate-600">Powstanie po domknięciu aktualnego zakresu.</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-action">Aktualny krok</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">{marketerWorkflowStepTitle(step.id)}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-5 text-slate-700">{instruction}</p>
        </div>
        <button
          type="button"
          onClick={() => (planNeedsRefresh ? onFocusPlan() : canAdvance && nextStep ? onAdvance(nextStep.id) : onFocusCurrentStep())}
          className="inline-flex h-10 w-full items-center justify-center rounded-md bg-action px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 lg:w-auto"
        >
          {actionLabel}
        </button>
      </div>
    </section>
  );
}

export function workflowStepActionLabel(stepId: WorkflowStepId, blocked: boolean): string {
  if (blocked && stepId === "dev_draft") return "Sprawdź blokadę dev preview";
  if (blocked && stepId === "review") return "Sprawdź blokadę review";
  if (stepId === "scope") return "Otwórz kontekst strony";
  if (stepId === "section_map") return "Otwórz tekst";
  if (stepId === "draft") return "Otwórz pełny draft";
  if (stepId === "review") return "Otwórz review wersji";
  return "Otwórz dev preview";
}

export function workflowStepInstruction(
  stepId: WorkflowStepId,
  blocker?: { label: string; reason: string } | null
) {
  if (blocker) return `${blocker.label}: ${blocker.reason}`;
  if (stepId === "scope") return "Sprawdź aktualny kontekst strony i zapisz jedną decyzję. WILQ sam zbuduje plan i otworzy tekst.";
  if (stepId === "section_map") return "Plan powstaje automatycznie; po jego odświeżeniu przejdziesz bezpośrednio do tekstu.";
  if (stepId === "draft") return "Przeczytaj pełny draft HTML. Edycja pozostaje w docelowym WordPressie; tutaj sprawdzasz wynik, źródła i gotowość do review.";
  if (stepId === "review") return "Uruchom advisory review, przeczytaj findings i zapisz własną decyzję dla exact revision.";
  return "Sprawdź revision-bound dev preview i przygotuj draft-only handoff. Publikacja pozostaje wyłączona.";
}

function focusWorkflowStep(stepId: WorkflowStepId) {
  const targetId = stepId === "scope" ? "planning-review-scope" : stepId === "section_map" ? "content-planning-generation" : stepId === "draft" ? "content-draft-workbench" : stepId === "review" ? "review-workspace-title" : "wordpress-draft-action-wizard";
  document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function ContentSessionPicker({
  workflowStatusLabel,
  queue,
  inventory,
  selectedWorkItemId,
  onSelectWorkItem,
  serviceLabel,
  pageTitle,
  pageUrl
}: {
  workflowStatusLabel: string;
  queue: ContentWorkItemQueueResponse;
  inventory: ContentInventoryCatalogResponse | null;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
  serviceLabel: string;
  pageTitle: string;
  pageUrl: string | null | undefined;
}) {
  const candidates = queue.candidates.filter(
    (candidate) => candidate.recommended_mode !== "block"
  );
  const [pageSearch, setPageSearch] = useState("");
  const allInventoryPageOptions = (inventory?.items ?? [])
    .map((item) => ({
      workItemId: item.work_item_id,
      label: `${item.title || item.path} — ${item.path}`
    }));
  const pageOptions = [
    ...candidates.map((candidate) => ({
      workItemId: candidate.work_item_id,
      label: `${candidate.title || candidate.topic} — ${contentCandidatePath(candidate.final_canonical_url)}`
    })),
    ...allInventoryPageOptions.filter(
      (item) => !candidates.some((candidate) => candidate.work_item_id === item.workItemId)
    )
  ];
  if (!pageOptions.some((item) => item.workItemId === selectedWorkItemId)) {
    pageOptions.unshift({
      workItemId: selectedWorkItemId,
      label: `${pageTitle} — ${contentCandidatePath(pageUrl)}`
    });
  }
  const filteredPageOptions = filterInventoryPageOptions(pageOptions, pageSearch);
  const selectedPageOption = pageOptions.find((item) => item.workItemId === selectedWorkItemId);
  const visiblePageOptions = selectedPageOption && !filteredPageOptions.some((item) => item.workItemId === selectedWorkItemId)
    ? [selectedPageOption, ...filteredPageOptions.slice(0, 29)]
    : filteredPageOptions;

  return (
    <section
      aria-labelledby="content-session-picker-title"
      className="wilq-enter mb-3 rounded-md border border-line bg-white px-3 py-3 shadow-sm sm:mb-4 sm:px-4"
      data-testid="content-session-picker"
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(15rem,22rem)] lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Strona</p>
          <h2 id="content-session-picker-title" className="mt-1 text-xl font-semibold text-ink">
            {pageTitle}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {contentCandidatePath(pageUrl)}
          </p>
          <p className="mt-2 text-xs text-slate-500">WordPress · {workflowStatusLabel}</p>
        </div>
        <div className="text-sm font-semibold text-ink">
          <label htmlFor="content-session-search">Szukaj strony</label>
          <input
            id="content-session-search"
            data-testid="content-session-search"
            type="search"
            value={pageSearch}
            onChange={(event) => setPageSearch(event.target.value)}
            placeholder="Tytuł lub URL"
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink"
          />
          <label className="mt-3 block" htmlFor="content-session-work-item">
            Strona
          </label>
          <select
            id="content-session-work-item"
            data-testid="content-session-work-item"
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink"
            value={selectedWorkItemId}
            onChange={(event) => onSelectWorkItem(event.target.value)}
          >
            {visiblePageOptions.map((item) => (
              <option key={item.workItemId} value={item.workItemId}>
                {item.label}
              </option>
            ))}
          </select>
          {inventory?.total_count ? (
            <span className="mt-1 block text-xs font-normal text-slate-500">
              {inventory.total_count.toLocaleString("pl-PL")} stron dostępnych · pokazano {visiblePageOptions.length}
            </span>
          ) : null}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1 border-t border-line pt-3 text-sm">
        <p className="font-semibold text-slate-500">Usługa:</p>
        <p className="font-semibold text-ink">{serviceLabel}</p>
      </div>
    </section>
  );
}

export function filterInventoryPageOptions(
  options: Array<{ workItemId: string; label: string }>,
  search: string,
  limit = 30
): Array<{ workItemId: string; label: string }> {
  const normalizedSearch = search.trim().toLocaleLowerCase("pl-PL");
  return options
    .filter((item) => !normalizedSearch || item.label.toLocaleLowerCase("pl-PL").includes(normalizedSearch))
    .slice(0, Math.max(1, limit));
}

function contentCandidatePath(url: string | null | undefined) {
  if (!url) return "adres do sprawdzenia";
  try {
    return new URL(url).pathname || "/";
  } catch {
    return "adres do sprawdzenia";
  }
}

function useContentWorkflowActions(
  data: ContentWorkflowSnapshot,
  selectedWorkItemId: string,
  authoringProfile: WordPressAuthoringProfile | null,
  operatorLabel: string
) {
  const mutations = useContentWorkflowMutations(selectedWorkItemId, operatorLabel);
  return contentWorkflowActions(data, mutations, authoringProfile, operatorLabel);
}

function useContentWorkflowMutations(selectedWorkItemId: string, operatorLabel: string) {
  const queryClient = useQueryClient();
  const refreshRevisionWorkspace = () =>
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "work-item", selectedWorkItemId]
    });
  const revisionSaveMutation = useMutation({
    mutationFn: (request: ContentDraftRevisionSaveRequest) =>
      saveContentWorkItemDraftRevision(request, selectedWorkItemId),
    onSuccess: (result) => {
      if (result.status !== "conflict") void refreshRevisionWorkspace();
    }
  });
  const planningReviewMutation = useMutation({
    mutationFn: (request: ContentPlanningReviewRequest) =>
      saveContentWorkItemPlanningReview(request, selectedWorkItemId),
    onSuccess: (result) => {
      if (!("detail" in result)) {
        void Promise.all([
          refreshRevisionWorkspace(),
          queryClient.invalidateQueries({
            queryKey: [
              "content-workflow",
              "work-item",
              selectedWorkItemId,
              "planning-proposal"
            ]
          })
        ]);
      }
    }
  });
  const revisionReviewMutation = useMutation({
    mutationFn: ({
      request,
      revisionId
    }: {
      request: ContentDraftRevisionReviewRequest;
      revisionId: string;
    }) => saveContentWorkItemDraftRevisionReview(request, selectedWorkItemId, revisionId),
    onSuccess: (result) => {
      if (result.status !== "conflict") void refreshRevisionWorkspace();
    }
  });
  const codexProposalMutation = useMutation({
    mutationFn: ({
      baseRevision,
      selection
    }: CodexProposalMutationInput) =>
      postContentWorkItemCodexSectionProposal(
        {
          expected_base_digest: baseRevision.content_digest,
          selected_section_headings:
            "sectionHeadings" in selection ? selection.sectionHeadings : [],
          selected_section_ids: "sectionIds" in selection ? selection.sectionIds : [],
          requested_by: operatorLabel
        },
        selectedWorkItemId,
        baseRevision.revision_id
      )
  });
  const initialDraftMutation = useMutation({
    mutationFn: (proposal: InitialDraftMutationInput) => {
      if (!proposal?.proposal_id || !proposal.planning_input_digest) {
        throw new Error("Bieżący plan nie ma exact bindingu do pełnego tekstu.");
      }
      return postContentWorkItemInitialDraft(
        {
          expected_proposal_id: proposal.proposal_id,
          expected_planning_digest: proposal.planning_digest,
          expected_planning_input_digest: proposal.planning_input_digest,
          requested_by: operatorLabel
        },
        selectedWorkItemId
      );
    },
    onSuccess: (result) => {
      queryClient.setQueryData(
        ["content-workflow", "initial-draft", selectedWorkItemId],
        result
      );
      if (result.status === "created") void refreshRevisionWorkspace();
    }
  });
  const initialDraftStatusQuery = useQuery({
    queryKey: ["content-workflow", "initial-draft", selectedWorkItemId],
    queryFn: () => getContentWorkItemInitialDraft(selectedWorkItemId),
    // Status is API-owned and must survive a browser reload.  The GET is
    // read-only; only a generating response enables the 2-second poll.
    enabled: Boolean(selectedWorkItemId),
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? 2000 : false
  });
  const initialDraftStatus = initialDraftStatusQuery.data;
  useEffect(() => {
    const result = initialDraftStatus;
    if (result?.status !== "created" || !result.revision?.revision_id) return;
    // The status poll has its own query key.  Refresh the canonical snapshot
    // once the worker has persisted the revision so the page preview, editor,
    // and review step switch from "generating" to the exact document without
    // requiring a manual reload.
    void queryClient.invalidateQueries({
      queryKey: ["content-workflow", "work-item", selectedWorkItemId]
    });
  }, [initialDraftStatus, queryClient, selectedWorkItemId]);
  const semanticReviewMutation = useMutation({
    mutationFn: ({ revisionId, revisionDigest }: { revisionId: string; revisionDigest: string }) =>
      postContentWorkItemSemanticReview(
        {
          expected_revision_digest: revisionDigest,
          requested_by: operatorLabel
        },
        selectedWorkItemId,
        revisionId
      ),
    onSuccess: (result: ContentSemanticReviewResponse) => {
      if (result.revision_id) {
        void queryClient.invalidateQueries({
          queryKey: [
            "content-workflow",
            "semantic-review",
            selectedWorkItemId,
            result.revision_id
          ]
        });
      }
    }
  });
  const acfPreviewMutation = useMutation({
    mutationFn: postContentWorkItemWordPressAuthoringPayloadPreview
  });
  const executionMutation = useMutation({ mutationFn: postContentWorkItemWordPressDraftExecution });
  return {
    planningReviewMutation,
    revisionSaveMutation,
    revisionReviewMutation,
    codexProposalMutation,
    initialDraftMutation,
    initialDraftStatusQuery,
    semanticReviewMutation,
    acfPreviewMutation,
    executionMutation,
    refreshRevisionWorkspace
  };
}

function contentWorkflowActions(
  data: ContentWorkflowSnapshot,
  mutations: ContentWorkflowMutations,
  authoringProfile: WordPressAuthoringProfile | null,
  operatorLabel: string
) {
  const latestRevision = data.revisionWorkspace.latest_revision;
  const revisionEvidenceIds = latestRevision
    ? [...new Set(latestRevision.sections.flatMap((section) => section.evidence_ids))]
    : [];
  return {
    planningReviewPending: mutations.planningReviewMutation.isPending,
    planningReviewConflict:
      mutations.planningReviewMutation.data && "detail" in mutations.planningReviewMutation.data
        ? mutations.planningReviewMutation.data
        : null,
    planningReviewError: mutations.planningReviewMutation.error,
    refreshPlanningWorkspace: () => {
      void mutations
        .refreshRevisionWorkspace()
        .finally(() => mutations.planningReviewMutation.reset());
    },
    savePlanningReview: (
      stage: "scope" | "section_map",
      decision: "approved" | "needs_changes",
      notes: string,
      checkedItems: string[],
      serviceCardId?: string
    ) => {
      const planning = data.planningWorkspace;
      if (!planning) return;
      mutations.planningReviewMutation.mutate({
        stage,
        expected_planning_digest: planning.proposal.planning_digest,
        service_card_id: stage === "scope" ? serviceCardId : undefined,
        decision,
        reviewed_by: operatorLabel,
        checked_items: checkedItems,
        notes
      });
    },
    revisionSavePending: mutations.revisionSaveMutation.isPending,
    revisionSaveConflict:
      mutations.revisionSaveMutation.data?.status === "conflict"
        ? mutations.revisionSaveMutation.data
        : null,
    revisionSaveError: mutations.revisionSaveMutation.error,
    revisionReviewPending: mutations.revisionReviewMutation.isPending,
    revisionReviewConflict:
      mutations.revisionReviewMutation.data?.status === "conflict"
        ? mutations.revisionReviewMutation.data
        : null,
    revisionReviewError: mutations.revisionReviewMutation.error,
    codexProposalPending: mutations.codexProposalMutation.isPending,
    codexProposalError: mutations.codexProposalMutation.error,
    codexProposalResult: mutations.codexProposalMutation.data ?? null,
    codexProposalBaseRevision:
      mutations.codexProposalMutation.variables?.baseRevision ?? null,
    initialDraftPending: mutations.initialDraftMutation.isPending,
    initialDraftError: mutations.initialDraftMutation.error,
    initialDraftResult:
      mutations.initialDraftMutation.data ?? mutations.initialDraftStatusQuery.data ?? null,
    generateInitialDraft: () => {
      const proposal = data.planningWorkspace?.proposal;
      if (proposal) mutations.initialDraftMutation.mutate(proposal);
    },
    semanticReviewPending: mutations.semanticReviewMutation.isPending,
    semanticReviewError: mutations.semanticReviewMutation.error,
    semanticReviewResult: mutations.semanticReviewMutation.data ?? null,
    generateSemanticReview: () => {
      if (!latestRevision) return;
      mutations.semanticReviewMutation.mutate({
        revisionId: latestRevision.revision_id,
        revisionDigest: latestRevision.content_digest
      });
    },
    acfPreviewPending: mutations.acfPreviewMutation.isPending,
    executionPending: mutations.executionMutation.isPending,
    authoringProfileReady: Boolean(authoringProfile),
    acfPreviewResult: acfPreviewResultFrom(mutations.acfPreviewMutation.data),
    executionResult: executionResultFrom(mutations.executionMutation.data),
    executionError: mutations.executionMutation.error,
    runCodexSectionProposal: (
      selection: { sectionIds: string[] } | { sectionHeadings: string[] }
    ) => {
      const selectedCount =
        "sectionIds" in selection ? selection.sectionIds.length : selection.sectionHeadings.length;
      if (!latestRevision || selectedCount === 0) return;
      mutations.codexProposalMutation.mutate({
        baseRevision: latestRevision,
        selection
      });
    },
    refreshCodexProposalWorkspace: () => {
      void mutations
        .refreshRevisionWorkspace()
        .finally(() => mutations.codexProposalMutation.reset());
    },
    saveDraftRevision: (title: string, sections: ContentDraftRevisionSection[]) =>
      mutations.revisionSaveMutation.mutate({
        base_revision_id: latestRevision?.revision_id ?? null,
        title,
        sections,
        created_by: operatorLabel
      }),
    saveRevisionReview: (
      decision: ContentDraftRevisionDecision,
      notes: string,
      checkedItems: string[]
    ) => {
      if (
        !latestRevision ||
        (decision === "approved" &&
          (revisionEvidenceIds.length === 0 || checkedItems.length < 2)) ||
        (decision !== "approved" && notes.trim().length === 0)
      ) {
        return;
      }
      mutations.revisionReviewMutation.mutate({
        revisionId: latestRevision.revision_id,
        request: {
          expected_revision_digest: latestRevision.content_digest,
          reviewed_by: operatorLabel,
          decision,
          notes,
          checked_items: checkedItems,
          evidence_ids: revisionEvidenceIds
        }
      });
    },
    runAcfPreview: () =>
      submitIfReady(
        acfPreviewRequest(
          data.draftPackage.draft_package_result.draft_package,
          data.wordpressHandoff.handoff_result.handoff,
          authoringProfile
        ),
        mutations.acfPreviewMutation.mutate
      ),
    runExecutionDryRun: () =>
      submitIfReady(
        wordpressExecutionRequest(
          data.draftPackage.draft_package_result.draft_package,
          data.wordpressHandoff.handoff_result.handoff
        ),
        mutations.executionMutation.mutate
      ),
    runExecutionDryRunWithSections: (sectionOverrides: WordPressDraftSectionOverride[]) =>
      submitIfReady(
        wordpressExecutionRequest(
          data.draftPackage.draft_package_result.draft_package,
          data.wordpressHandoff.handoff_result.handoff,
          sectionOverrides
        ),
        mutations.executionMutation.mutate
      )
  };
}

type WordPressDraftSectionOverride = NonNullable<
  ContentWorkItemWordPressDraftExecutionRequest["section_overrides"]
>[number];
