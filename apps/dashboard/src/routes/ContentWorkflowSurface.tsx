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
import type { ContentWorkflowSnapshot, WorkflowStepId } from "./contentWorkflowRuntime";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { ContentInventoryCatalogPanel } from "./ContentInventoryCatalogPanel";
import { WorkflowStepsList } from "./WorkflowStepsList";
import {
  ContentWorkflowError,
  ContentWorkflowSelectedLoading,
  ContentWorkflowInventorySelectionLoading,
  ContentFreshnessBanner,
  type ContentSourceRefreshControl
} from "./ContentWorkflowBoundaryStates";
import { ContentOpportunityEnrichmentPanel } from "./ContentOpportunityEnrichmentPanel";
import { ClaimLedgerGatePanel } from "./ClaimLedgerGatePanel";
import { ContentWorkflowDecisionPanel } from "./ContentWorkflowDecisionPanel";
import { WordPressDraftWorkPanel as WordPressDraftWorkPanelView } from "./WordPressDraftWorkPanel";
import { ContentSectionWritingWorkbench as ContentSectionWritingWorkbenchView } from "./ContentSectionWritingWorkbench";
import { ContentWorkflowBlockedCandidate } from "./ContentWorkflowBlockedCandidate";
import { ContentPageWorkbench as ContentPageWorkbenchView } from "./ContentPageWorkbench";
import { ContentWorkflowJourneyContext } from "./ContentWorkflowJourneyContext";
import { ContentWorkflowTaskMap } from "./ContentWorkflowTaskMap";
import { ContentKnowledgeReadinessNotice } from "./ContentKnowledgeReadinessNotice";
import {
  acfPreviewResultFrom,
  acfPreviewRequest,
  executionResultFrom,
  submitIfReady,
  wordpressExecutionRequest
} from "./contentWorkflowActionModel";
import { WorkflowProofSummary } from "./WorkflowProofSummary";
import {
  useContentWorkflowQueries,
  type ContentOpportunityEnrichmentQuery,
  type ContentOperatorContextQuery,
  type ContentWorkItemQueueQuery,
  type ContentInventoryCatalogQuery,
  type ContentServiceProfileQuery,
  type ContentWorkflowSnapshotQuery,
  type KnowledgeSourceMaterialsQuery,
  type KnowledgeSourceMaterialReadinessQuery,
  type WordPressAuthoringProfileQuery,
  type WordPressDraftActivationPacketQuery,
  type WordPressDraftWriteReadinessQuery,
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
type ContentPlanningSections = NonNullable<
  ContentWorkflowSnapshot["planningWorkspace"]
>["proposal"]["sections"];
type ContentPlanningGenerationStatus = NonNullable<
  ContentWorkflowSnapshot["planningWorkspace"]
>["proposal"]["generation_status"];
export function ContentWorkflowSurface() {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const sourceRefresh = useContentSourceRefresh();
  const selectedWorkItemId = stringFromSearch(routeSearch, "work_item_id");
  const selectWorkItem = (workItemId: string) => {
    void navigate({
      to: "/content-workflow",
      search: (previous) => ({
        ...previous,
        work_item_id: workItemId,
        section_heading: undefined,
        planning_digest: undefined
      })
    });
  };
  const {
    activeWorkItemId,
    authoringProfile,
    draftActivationPacket,
    draftWriteReadiness,
    enrichment,
    inventory,
    knowledgeMaterials,
    knowledgeReadiness,
    operatorContext,
    serviceProfile,
    queue,
    selectedCandidate,
    workflow
  } = useContentWorkflowQueries(selectedWorkItemId);

  return (
    <ContentWorkflowRouteState
      activeWorkItemId={activeWorkItemId}
      selectedWorkItemId={selectedWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      inventory={inventory}
      knowledgeMaterials={knowledgeMaterials}
      knowledgeReadiness={knowledgeReadiness}
      operatorContext={operatorContext}
      serviceProfile={serviceProfile}
      queue={queue}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      sourceRefresh={sourceRefresh}
      onSelectWorkItem={selectWorkItem}
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
  draftWriteReadiness,
  enrichment,
  inventory,
  knowledgeMaterials,
  knowledgeReadiness,
  operatorContext,
  serviceProfile,
  queue,
  selectedCandidate,
  workflow,
  sourceRefresh,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
  selectedWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  inventory: ContentInventoryCatalogQuery;
  knowledgeMaterials: KnowledgeSourceMaterialsQuery;
  knowledgeReadiness: KnowledgeSourceMaterialReadinessQuery;
  operatorContext: ContentOperatorContextQuery;
  serviceProfile: ContentServiceProfileQuery;
  queue: ContentWorkItemQueueQuery;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  sourceRefresh: ContentSourceRefreshControl;
  onSelectWorkItem: (workItemId: string) => void;
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
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      inventory={inventory}
      knowledgeMaterials={knowledgeMaterials}
      knowledgeReadiness={knowledgeReadiness}
      operatorContext={operatorContext}
      serviceProfile={serviceProfile}
      queue={queue.data}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      sourceRefresh={sourceRefresh}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowQueueReady({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  inventory,
  knowledgeMaterials,
  knowledgeReadiness,
  operatorContext,
  serviceProfile,
  queue,
  selectedCandidate,
  workflow,
  sourceRefresh,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  inventory: ContentInventoryCatalogQuery;
  knowledgeMaterials: KnowledgeSourceMaterialsQuery;
  knowledgeReadiness: KnowledgeSourceMaterialReadinessQuery;
  operatorContext: ContentOperatorContextQuery;
  serviceProfile: ContentServiceProfileQuery;
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  sourceRefresh: ContentSourceRefreshControl;
  onSelectWorkItem: (workItemId: string) => void;
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
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
        queue={queue}
        inventory={inventory.data ?? null}
        selectedCandidate={selectedCandidate}
        workflow={workflow}
        sourceRefresh={sourceRefresh}
        onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function OverviewMetric({ label, value, accent = false, muted = false }: { label: string; value: number; accent?: boolean; muted?: boolean }) {
  return <div className={`rounded-xl border px-3 py-3 ${accent ? "border-action/20 bg-action/5" : muted ? "border-slate-200 bg-slate-50" : "border-slate-100 bg-white"}`}><div className={`text-2xl font-semibold ${accent ? "text-action" : muted ? "text-slate-500" : "text-ink"}`}>{value.toLocaleString("pl-PL")}</div><div className="mt-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</div></div>;
}

function ContentWorkflowSelectedReady({
  activeWorkItemId,
  authoringProfile,
  operatorLabel,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  inventory,
  selectedCandidate,
  workflow,
  sourceRefresh,
  onSelectWorkItem
}: {
  activeWorkItemId: string;
  authoringProfile: WordPressAuthoringProfileQuery;
  operatorLabel: string;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  inventory: ContentInventoryCatalogResponse | null;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  sourceRefresh: ContentSourceRefreshControl;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (selectedCandidate === null) return <ContentWorkflowError />;
  if (workflow.isLoading) {
    return (
      <ContentWorkflowSelectedLoading
        assessment={queue.freshness_assessment}
        candidate={selectedCandidate}
        refresh={sourceRefresh}
        refreshTargetUrl={selectedCandidate.final_canonical_url}
      />
    );
  }
  if (workflow.error || !workflow.data) {
    return (
      <ContentWorkflowSelectedLoading
        assessment={queue.freshness_assessment}
        candidate={selectedCandidate}
        error
        refresh={sourceRefresh}
        refreshTargetUrl={selectedCandidate.final_canonical_url}
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
      draftWriteReadiness={draftWriteReadiness}
      sourceRefresh={sourceRefresh}
      refreshTargetUrl={selectedCandidate.final_canonical_url}
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
  draftWriteReadiness,
  sourceRefresh,
  refreshTargetUrl,
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
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  sourceRefresh: ContentSourceRefreshControl;
  refreshTargetUrl?: string | null;
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
  const steps = data.operatorSteps;

  return (
    <main className="w-full px-4 py-3 sm:py-5 lg:px-7 2xl:px-8">
      <header className="mb-3 flex flex-wrap items-end justify-between gap-3 sm:mb-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-action">WILQ · Ekologus</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Treści i SEO</h1>
          <p className="mt-1 text-sm text-slate-600">Content workflow</p>
          <span className="sr-only">
            {viewMode === "marketer"
              ? "Decyzja, blocker i następny bezpieczny krok."
              : "Metryki, źródła i szczegóły do sprawdzenia przed przekazaniem."}
          </span>
        </div>
        <div className="flex rounded-md border border-line bg-white p-1 shadow-sm" role="group" aria-label="Tryb widoku">
          <button
            type="button"
            aria-label="Marketer"
            aria-pressed={viewMode === "marketer"}
            onClick={() => setViewMode("marketer")}
            className={`rounded px-3 py-2 text-sm font-semibold ${viewMode === "marketer" ? "sr-only" : ""} ${
              viewMode === "marketer" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Treści i SEO
          </button>
          <button
            type="button"
            aria-pressed={viewMode === "technical"}
            onClick={() => setViewMode("technical")}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "technical" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Źródła i szczegóły
          </button>
        </div>
      </header>

      {viewMode === "technical" ? (
        <ContentFreshnessBanner
          assessment={queue.freshness_assessment}
          refresh={sourceRefresh}
          refreshTargetUrl={refreshTargetUrl}
        />
      ) : null}

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
      />
      ) : (
        <section
          id="content-workflow-details"
          aria-label="Źródła i szczegóły workflow treści"
          className="mb-6 rounded-md border border-line bg-white p-4"
          data-testid="content-workflow-technical-audit"
        >
          <ContentWorkflowDecisionPanel data={data} queue={queue} steps={steps} />
          <WordPressDraftWorkPanelView
            actions={actions}
            authoringProfile={authoringProfile}
            draftActivationPacket={draftActivationPacket}
            draftWriteReadiness={draftWriteReadiness}
          />
          <ContentSectionWritingWorkbenchView
            actions={actions}
            authoringProfile={authoringProfile}
            data={data}
            draftActivationPacket={draftActivationPacket}
          />
          <ContentCandidateQueuePanel
            queue={queue}
            selectedWorkItemId={selectedWorkItemId}
            onSelectWorkItem={onSelectWorkItem}
          />
          <WorkflowProofSummary data={data} />
          <ClaimLedgerGatePanel data={data} />
          <ContentOpportunityEnrichmentPanel enrichment={enrichment} />
          <WorkflowStepsList steps={steps} />
        </section>
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
  onSelectWorkItem
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
}) {
  const [selectedStepId, setSelectedStepId] = useState<WorkflowStepId>(data.currentStepId);
  const selectStep = (stepId: WorkflowStepId) => {
    if (data.operatorSteps.some((step) => step.id === stepId && step.canOpen)) {
      setSelectedStepId(stepId);
    }
  };

  return (
    <div data-testid="content-workflow-marketer-journey">
      <ContentSessionPicker
        planningGenerationStatus={data.planningWorkspace?.proposal.generation_status ?? "baseline"}
        planningDigest={data.planningWorkspace?.proposal.planning_digest ?? null}
        planningSections={data.planningWorkspace?.proposal.sections ?? []}
        currentSectionHeadings={data.candidate.page_inventory?.section_headings ?? []}
        queue={queue}
        inventory={inventory}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
        activeStepId={selectedStepId}
        serviceLabel={data.serviceProfileContext.service_label ?? "Nieprzypisana usługa"}
      />
      <ContentNextStepHero
        step={data.operatorSteps.find((step) => step.id === selectedStepId) ?? data.operatorSteps[0]}
        nextStep={data.operatorSteps[data.operatorSteps.findIndex((step) => step.id === selectedStepId) + 1]}
        onAdvance={selectStep}
        onFocusCurrentStep={() => focusWorkflowStep(selectedStepId)}
        planningCurrent={selectedStepId === "scope" ? data.planningWorkspace?.scope_current ?? true : selectedStepId === "section_map" ? data.planningWorkspace?.section_map_current ?? true : true}
      />
      <div className="flex flex-col">
        <div className="order-1">
          <ContentWorkflowJourneyContext data={data} />
        </div>
        <div className="order-2">
          <ContentWorkflowTaskMap
            currentStepId={data.currentStepId}
            selectedStepId={selectedStepId}
            steps={data.operatorSteps}
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
        activeStepId={selectedStepId}
      />
    </div>
  );
}

function ContentNextStepHero({
  step,
  nextStep,
  onAdvance,
  onFocusCurrentStep,
  planningCurrent
}: {
  step: ContentWorkflowSnapshot["operatorSteps"][number] | undefined;
  nextStep: ContentWorkflowSnapshot["operatorSteps"][number] | undefined;
  onAdvance: (stepId: WorkflowStepId) => void;
  onFocusCurrentStep: () => void;
  planningCurrent: boolean;
}) {
  if (!step) return null;
  const canAdvance = Boolean(nextStep?.canOpen);
  const nextStepLabel = nextStep?.id === "section_map" ? "Przejdź do planu" : nextStep?.id === "draft" ? "Przejdź do tekstu" : nextStep?.id === "review" ? "Przejdź do review" : nextStep?.id === "dev_draft" ? "Przejdź do dev preview" : "Zobacz kolejny krok";
  const currentStepLabel = workflowStepActionLabel(step.id, Boolean(step.blocker));
  const actionLabel = canAdvance ? nextStepLabel : !planningCurrent ? "Sprawdź aktualny zakres" : currentStepLabel;
  const instruction = !planningCurrent
    ? "Poprzednia decyzja jest nieaktualna, bo zmienił się plan lub dowody. Sprawdź zakres jeszcze raz i zapisz aktualną decyzję."
    : nextStep?.canOpen
      ? step.safeNextStep
      : workflowStepInstruction(step.id);
  return (
    <section className="wilq-enter wilq-enter-delay-1 mb-3 rounded-md border border-action/30 bg-action/5 p-3 shadow-sm sm:mb-4 sm:p-5" data-testid="content-next-step-hero">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-action text-2xl text-white" aria-hidden="true">→</span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-action">Następny krok</p>
            <h2 className="mt-1 text-xl font-semibold text-ink">{step.title}</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-700">{instruction}</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => (canAdvance && nextStep ? onAdvance(nextStep.id) : onFocusCurrentStep())}
          className="inline-flex h-10 self-start items-center justify-center rounded-md bg-action px-4 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:self-auto sm:text-sm"
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
  if (stepId === "scope") return "Otwórz formularz zakresu";
  if (stepId === "section_map") return "Otwórz plan strony";
  if (stepId === "draft") return "Otwórz edytor tekstu";
  if (stepId === "review") return "Otwórz review wersji";
  return "Otwórz dev preview";
}

function workflowStepInstruction(stepId: WorkflowStepId) {
  if (stepId === "scope") return "Potwierdź usługę, sprawdź cel i odbiorcę briefu, zaznacz potwierdzenie i zapisz decyzję. WILQ sam zbuduje mapę sekcji.";
  if (stepId === "section_map") return "Sprawdź automatycznie wykrytą strukturę strony, przypisane zapytania i page assets. Nie mapujesz sekcji ręcznie.";
  if (stepId === "draft") return "Przeczytaj pełny tekst, wybierz sekcję do poprawy albo zapisz exact revision do review.";
  if (stepId === "review") return "Uruchom advisory review, przeczytaj findings i zapisz własną decyzję dla exact revision.";
  return "Sprawdź revision-bound dev preview i przygotuj draft-only handoff. Publikacja pozostaje wyłączona.";
}

function focusWorkflowStep(stepId: WorkflowStepId) {
  const targetId = stepId === "scope" ? "planning-review-scope" : stepId === "section_map" ? "planning-review-section_map" : stepId === "draft" ? "draft-section-tabs" : stepId === "review" ? "review-workspace-title" : "wordpress-draft-action-wizard";
  document.getElementById(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function ContentSessionPicker({
  planningGenerationStatus,
  planningDigest,
  planningSections,
  currentSectionHeadings,
  queue,
  inventory,
  selectedWorkItemId,
  onSelectWorkItem,
  activeStepId,
  serviceLabel
}: {
  planningGenerationStatus: ContentPlanningGenerationStatus;
  planningDigest: string | null;
  planningSections: ContentPlanningSections;
  currentSectionHeadings: string[];
  queue: ContentWorkItemQueueResponse;
  inventory: ContentInventoryCatalogResponse | null;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
  activeStepId: WorkflowStepId;
  serviceLabel: string;
}) {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const requestedSectionHeading = stringFromSearch(routeSearch, "section_heading");
  const requestedPlanningDigest = stringFromSearch(routeSearch, "planning_digest");
  const [inventorySearch, setInventorySearch] = useState("");
  const candidates = queue.candidates.filter(
    (candidate) => candidate.recommended_mode !== "block"
  );
  const queueCandidateIds = new Set(candidates.map((candidate) => candidate.work_item_id));
  const allInventoryPageOptions = (inventory?.items ?? [])
    .filter((item) => !queueCandidateIds.has(item.work_item_id))
    .map((item) => ({
      workItemId: item.work_item_id,
      label: `${item.title || item.path} — ${item.path}`
    }));
  const inventoryPageOptions = filterInventoryPageOptions(allInventoryPageOptions, inventorySearch);
  const selected = candidates.find(
    (candidate) => candidate.work_item_id === selectedWorkItemId
  );
  const hasGeneratedPlan = planningGenerationStatus === "codex_generated";
  const selectedSectionHeading = hasGeneratedPlan
    ? (requestedPlanningDigest === planningDigest
        ? planningSections.find((section) => section.heading === requestedSectionHeading)?.heading
        : null) ?? planningSections[0]?.heading ?? null
    : (!requestedPlanningDigest &&
        requestedSectionHeading &&
        currentSectionHeadings.includes(requestedSectionHeading)
        ? requestedSectionHeading
        : null) ?? currentSectionHeadings[0] ?? null;
  const availableSectionHeadings = hasGeneratedPlan
    ? planningSections.map((section) => section.heading)
    : currentSectionHeadings;
  if (!selected) return null;

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
            {selected.topic}
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            {contentCandidatePath(selected.final_canonical_url)}
          </p>
          <p className="mt-2 text-xs text-slate-500">WordPress · {selected.status_label}</p>
        </div>
        <label className="text-sm font-semibold text-ink" htmlFor="content-session-work-item">
          Aktywna strona
          <select
            id="content-session-work-item"
            data-testid="content-session-work-item"
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink"
            value={selectedWorkItemId}
            onChange={(event) => onSelectWorkItem(event.target.value)}
          >
            {candidates.map((candidate) => (
              <option key={candidate.work_item_id} value={candidate.work_item_id}>
                {candidate.topic} — {contentCandidatePath(candidate.final_canonical_url)}
              </option>
            ))}
            {selectedWorkItemId && !queueCandidateIds.has(selectedWorkItemId)
              ? allInventoryPageOptions
                  .filter((item) => item.workItemId === selectedWorkItemId)
                  .map((item) => <option key={item.workItemId} value={item.workItemId}>{item.label}</option>)
              : null}
          </select>
        </label>
      </div>
      <div className="mt-4 flex items-center gap-3 rounded-md border border-action/20 bg-action/5 p-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-action text-lg font-semibold text-white" aria-hidden="true">↗</span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Usługa</p>
          <p className="mt-1 font-semibold text-ink">{serviceLabel}</p>
          <p className="text-xs text-slate-600">Dopasowanie na podstawie strony i danych WILQ</p>
        </div>
      </div>
      <details className="mt-3 rounded-md border border-line bg-surface px-3 py-2 text-sm">
        <summary className="cursor-pointer font-semibold text-action">Zmień stronę lub otwórz pełny inventory</summary>
        <div className="mt-3 space-y-3" aria-label="Strony dostępne do odświeżenia">
          <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
            Szukaj w pełnym inventory WordPress
            <input
              type="search"
              value={inventorySearch}
              onChange={(event) => setInventorySearch(event.target.value)}
              placeholder="Tytuł albo adres URL"
              className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm font-normal normal-case tracking-normal text-ink"
              aria-label="Szukaj w pełnym inventory WordPress"
            />
          </label>
          <div className="grid gap-2 lg:grid-cols-2">
          {candidates.map((candidate) => (
            <button
              key={candidate.work_item_id}
              type="button"
              onClick={() => onSelectWorkItem(candidate.work_item_id)}
              className={`rounded-md border p-3 text-left transition-colors ${
                candidate.work_item_id === selectedWorkItemId
                  ? "border-action bg-action/10"
                  : "border-line bg-white hover:border-action/50"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-ink">{contentCandidatePath(candidate.final_canonical_url)}</span>
                <span className="text-xs font-semibold text-slate-500">{candidate.recommended_mode_label}</span>
              </div>
              <p className="mt-1 text-sm text-slate-700">{candidate.topic}</p>
              <p className="mt-2 text-xs leading-5 text-slate-600">{pageMetricsSummary(candidate)}</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">{pageInventorySummary(candidate)}</p>
              {candidate.page_inventory?.acf_section_headings.length ? (
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Układ ACF: {acfSectionPreview(candidate.page_inventory.acf_section_headings)}
                </p>
              ) : null}
            </button>
          ))}
          {inventoryPageOptions.map((item) => (
            <button
              key={item.workItemId}
              type="button"
              onClick={() => onSelectWorkItem(item.workItemId)}
              className={`rounded-md border p-3 text-left transition-colors ${item.workItemId === selectedWorkItemId ? "border-action bg-action/10" : "border-line bg-white hover:border-action/50"}`}
            >
              <span className="font-semibold text-ink">{item.label}</span>
              <p className="mt-1 text-xs text-slate-500">Pełny inventory WordPress · wybierz, aby odczytać stronę i metryki.</p>
            </button>
          ))}
          {!inventoryPageOptions.length ? <p className="text-sm text-slate-600">Brak stron pasujących do wyszukiwania.</p> : null}
          </div>
          {allInventoryPageOptions.length > inventoryPageOptions.length ? <p className="text-xs text-slate-500">Pokazuję maksymalnie 30 wyników. Doprecyzuj wyszukiwanie, aby znaleźć konkretny adres.</p> : null}
        </div>
      </details>
      {selectedSectionHeading && !["scope", "section_map"].includes(activeStepId) ? (
        <label className="mt-3 block text-sm font-semibold text-ink" htmlFor="content-session-section">
          {hasGeneratedPlan ? "Przejdź do sekcji z planu" : "Przejdź do sekcji strony"}
          <select
            id="content-session-section"
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink"
            value={selectedSectionHeading}
            onChange={(event) => {
              void navigate({
                to: "/content-workflow",
                search: (previous) => ({
                  ...previous,
                  work_item_id: selectedWorkItemId,
                  section_heading: event.target.value,
                  planning_digest: hasGeneratedPlan ? planningDigest ?? undefined : undefined
                }),
                replace: true
              });
            }}
          >
            {availableSectionHeadings.map((heading) => (
              <option key={heading} value={heading}>
                {heading}
              </option>
            ))}
          </select>
        </label>
      ) : null}
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

function pageMetricsSummary(candidate: ContentWorkItemQueueCandidate) {
  const metrics = candidate.search_metrics;
  if (!metrics || metrics.impressions === null || metrics.impressions === undefined) {
    return "Brakuje danych z wyszukiwarki dla tej strony.";
  }
  const values = [`${metrics.impressions} wyświetleń`];
  if (metrics.clicks !== null && metrics.clicks !== undefined) values.push(`${metrics.clicks} kliknięć`);
  if (metrics.ctr !== null && metrics.ctr !== undefined) values.push(`CTR ${(metrics.ctr * 100).toFixed(2)}%`);
  if (metrics.primary_query) values.push(`najczęściej: „${metrics.primary_query}”`);
  if (metrics.comparison_status === "available" && metrics.comparison_periods?.length === 2) {
    values.push(`porównanie: ${metrics.comparison_periods[0]} → ${metrics.comparison_periods[1]}`);
  } else {
    values.push("brak dwóch porównywalnych okresów");
  }
  if (candidate.ga4_metrics?.status === "available" && candidate.ga4_metrics.metrics.length) {
    values.push(
      `GA4: ${candidate.ga4_metrics.metrics
        .slice(0, 3)
        .map((metric) => `${metric.metric_label || metric.name} ${metric.value}`)
        .join(", ")}`
    );
  } else {
    values.push("GA4: brak exact danych");
  }
  return values.join(" · ");
}

function pageInventorySummary(candidate: ContentWorkItemQueueCandidate) {
  const inventory = candidate.page_inventory;
  if (!inventory) return "Stan aktualnej strony wymaga odczytu.";
  const sections =
    inventory.section_inventory_status === "available" && inventory.section_count !== null
      ? `${inventory.section_count} rozpoznanych sekcji`
      : "sekcje wymagają odczytu";
  const layout =
    inventory.acf_section_inventory_status === "available"
      ? `${inventory.acf_section_count ?? ""} sekcji ACF`.trim()
      : inventory.content_inventory_status === "available"
        ? "treść w the_content · bez sekcji ACF"
      : "układ strony wymaga odczytu";
  return `${sections} · ${layout}`;
}

function acfSectionPreview(headings: string[]) {
  const visible = headings.slice(0, 2).join(" · ");
  const remaining = headings.length - 2;
  return remaining > 0 ? `${visible} · +${remaining}` : visible;
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
      mutations.initialDraftStatusQuery.data ?? mutations.initialDraftMutation.data ?? null,
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
