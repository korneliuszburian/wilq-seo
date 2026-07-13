import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  postContentWorkItemQualityReview,
  postContentWorkItemRevisionPlan,
  postContentWorkItemStructuredDraftPreview,
  postContentWorkItemStructuredDraftRuntime,
  postContentWorkItemWordPressAuthoringPayloadPreview,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemSnapshotAudit,
  saveContentWorkItemSnapshotHumanReview,
  type ContentWorkItemSnapshotAuditRequest,
  type ContentWorkItemSnapshotHumanReviewRequest,
  type ContentWorkItemQualityReviewRequest,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemRevisionPlanRequest,
  type ContentWorkItemStructuredDraftPreviewRequest,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentOpportunityEnrichment,
  type WordPressAuthoringProfile
} from "../lib/api";
import {
  buildWorkflowSteps,
  type ContentWorkflowSnapshot
} from "./contentWorkflowRuntime";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { WorkflowStepsList } from "./WorkflowStepsList";
import {
  ContentWorkflowError,
  ContentWorkflowEmptyQueue,
  ContentWorkflowSelectedLoading
} from "./ContentWorkflowBoundaryStates";
import { ContentOpportunityEnrichmentPanel } from "./ContentOpportunityEnrichmentPanel";
import { ClaimLedgerGatePanel } from "./ClaimLedgerGatePanel";
import { WorkflowSafetyPanels } from "./WorkflowSafetyPanels";
import { MobileContentTriage } from "./MobileContentTriage";
import { ContentWorkflowDecisionPanel } from "./ContentWorkflowDecisionPanel";
import { WordPressDraftWorkPanel as WordPressDraftWorkPanelView } from "./WordPressDraftWorkPanel";
import { ContentSectionWritingWorkbench as ContentSectionWritingWorkbenchView } from "./ContentSectionWritingWorkbench";
import {
  WorkflowOperatorControls as WorkflowOperatorControlsView,
  type WorkflowControlItem
} from "./WorkflowOperatorControls";
import { ContentWorkflowBlockedCandidate } from "./ContentWorkflowBlockedCandidate";
import { ContentPageWorkbench as ContentPageWorkbenchView } from "./ContentPageWorkbench";
import {
  acfPreviewResultFrom,
  acfPreviewRequest,
  auditRequest,
  executionResultFrom,
  humanReviewRequest,
  previewResultFrom,
  qualityReviewFrom,
  qualityReviewRequest,
  revisionPlanFrom,
  revisionPlanRequest,
  runtimeResultFrom,
  structuredPreviewRequest,
  structuredRuntimeDryRunRequest,
  submitIfReady,
  wordpressExecutionRequest
} from "./contentWorkflowActionModel";
import {
  acfPreviewSafetyText,
  acfPreviewControlDisabledReason,
  auditControlDisabledReason,
  draftSafetyText,
  executionControlDisabledReason,
  handoffSafetyText,
  measurementSafetyText,
  qualityReviewControlDisabledReason,
  qualityReviewSafetyText,
  revisionPlanControlDisabledReason,
  revisionPlanSafetyText,
  reviewControlDisabledReason,
  structuredPreviewControlDisabledReason,
  structuredPreviewSafetyText,
  structuredRuntimeControlDisabledReason,
  structuredRuntimeSafetyText,
  wordpressExecutionSafetyText
} from "./contentWorkflowSafetyModel";
import { WorkflowProofSummary } from "./WorkflowProofSummary";
import {
  useContentWorkflowQueries,
  type ContentOpportunityEnrichmentQuery,
  type ContentWorkItemQueueQuery,
  type ContentWorkflowSnapshotQuery,
  type WordPressAuthoringProfileQuery,
  type WordPressDraftActivationPacketQuery,
  type WordPressDraftWriteReadinessQuery,
  type ContentWorkItemQueueCandidate
} from "./contentWorkflowQueries";

type ContentWorkflowActions = ReturnType<typeof useContentWorkflowActions>;
type ContentWorkflowMutations = ReturnType<typeof useContentWorkflowMutations>;
export function ContentWorkflowSurface() {
  const [selectedWorkItemId, setSelectedWorkItemId] = useState<string | null>(null);
  const {
    activeWorkItemId,
    authoringProfile,
    draftActivationPacket,
    draftWriteReadiness,
    enrichment,
    queue,
    selectedCandidate,
    workflow
  } = useContentWorkflowQueries(selectedWorkItemId);

  return (
    <ContentWorkflowRouteState
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      queue={queue}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      onSelectWorkItem={setSelectedWorkItemId}
    />
  );
}

function ContentWorkflowRouteState({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueQuery;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (queue.isLoading) return <LoadingBand />;
  if (queue.error || !queue.data) return <ContentWorkflowError />;
  return (
    <ContentWorkflowQueueReady
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      queue={queue.data}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
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
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string | null;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (!activeWorkItemId) return <ContentWorkflowEmptyQueue queue={queue} />;
  if (selectedCandidate?.recommended_mode === "block") {
    return (
      <ContentWorkflowBlockedCandidate
        queue={queue}
        selectedCandidate={selectedCandidate}
        selectedWorkItemId={activeWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
    );
  }
  return (
    <ContentWorkflowSelectedReady
      activeWorkItemId={activeWorkItemId}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment}
      queue={queue}
      selectedCandidate={selectedCandidate}
      workflow={workflow}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowSelectedReady({
  activeWorkItemId,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedCandidate,
  workflow,
  onSelectWorkItem
}: {
  activeWorkItemId: string;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichmentQuery;
  queue: ContentWorkItemQueueResponse;
  selectedCandidate: ContentWorkItemQueueCandidate | null;
  workflow: ContentWorkflowSnapshotQuery;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  if (selectedCandidate === null) return <ContentWorkflowError />;
  if (workflow.isLoading) {
    return (
      <ContentWorkflowSelectedLoading
        assessment={queue.freshness_assessment}
        candidate={selectedCandidate}
      />
    );
  }
  if (workflow.error || !workflow.data) {
    return (
      <ContentWorkflowSelectedLoading
        assessment={queue.freshness_assessment}
        candidate={selectedCandidate}
        error
      />
    );
  }
  return (
    <ContentWorkflowLoaded
      data={workflow.data}
      authoringProfile={authoringProfile}
      draftActivationPacket={draftActivationPacket}
      draftWriteReadiness={draftWriteReadiness}
      enrichment={enrichment.data?.enrichment ?? null}
      queue={queue}
      selectedWorkItemId={activeWorkItemId}
      onSelectWorkItem={onSelectWorkItem}
    />
  );
}

function ContentWorkflowLoaded({
  data,
  authoringProfile,
  draftActivationPacket,
  draftWriteReadiness,
  enrichment,
  queue,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  data: ContentWorkflowSnapshot;
  authoringProfile: WordPressAuthoringProfileQuery;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  draftWriteReadiness: WordPressDraftWriteReadinessQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const actions = useContentWorkflowActions(
    data,
    selectedWorkItemId,
    authoringProfile.data ?? null
  );
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"marketer" | "technical">("marketer");
  const draft = data.draftPackage.draft_package_result.draft_package;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  const window = data.measurementWindow.measurement_window_result.window;
  const steps = buildWorkflowSteps(data);

  return (
    <main className="w-full px-4 py-5 lg:px-7 2xl:px-8">
      <div className="lg:hidden">
        <MobileContentTriage data={data} onOpenDetails={() => setDetailsOpen(true)} />
      </div>
      <section className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-white px-4 py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Widok pracy</p>
          <p className="mt-1 text-sm text-slate-700">
            {viewMode === "marketer"
              ? "Decyzja, blocker i następny bezpieczny krok."
              : "Dowody, audyt i kontrakty do sprawdzenia technicznego."}
          </p>
        </div>
        <div className="flex rounded-md border border-line bg-surface p-1" role="group" aria-label="Tryb widoku">
          <button
            type="button"
            aria-pressed={viewMode === "marketer"}
            onClick={() => {
              setViewMode("marketer");
              setDetailsOpen(false);
            }}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "marketer" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Marketer
          </button>
          <button
            type="button"
            aria-pressed={viewMode === "technical"}
            onClick={() => {
              setViewMode("technical");
              setDetailsOpen(true);
            }}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "technical" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Audyt techniczny
          </button>
        </div>
      </section>
          <ContentPageWorkbenchView
            actions={actions}
            authoringProfile={authoringProfile}
            data={data}
            draftActivationPacket={draftActivationPacket}
            enrichment={enrichment}
            queue={queue}
            onOpenDetails={() => setDetailsOpen(true)}
          />
      <details
        id="content-workflow-details"
        className="mb-6 rounded-md border border-line bg-white"
        open={detailsOpen}
        onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
      >
        <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-ink">
          {viewMode === "technical"
            ? "Audyt techniczny: workflow, kolejka i ślad działania"
            : "Szczegóły workflow, kolejka i audyt techniczny"}
        </summary>
        {detailsOpen ? (
          <div className="border-t border-line p-4">
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
            <WorkflowOperatorControlsView
              controls={workflowControlItems(data, actions)}
              topic={data.preflight.item.topic}
            />
            <WorkflowProofSummary data={data} />
            <ClaimLedgerGatePanel data={data} />
            <ContentOpportunityEnrichmentPanel enrichment={enrichment} />
            <WorkflowStepsList steps={steps} />
            <WorkflowSafetyPanels
              structuredPreviewResult={actions.structuredPreviewResult}
              draftSafetyText={draftSafetyText(draft?.publish_ready)}
              structuredRuntimeSafetyText={structuredRuntimeSafetyText(actions.structuredRuntimeResult)}
              structuredPreviewSafetyText={structuredPreviewSafetyText(actions.structuredPreviewResult)}
              qualityReviewSafetyText={qualityReviewSafetyText(actions.qualityReview)}
              revisionPlanSafetyText={revisionPlanSafetyText(actions.revisionPlan)}
              acfPreviewSafetyText={acfPreviewSafetyText(actions.acfPreviewResult)}
              handoffSafetyText={handoffSafetyText(handoff?.publish_allowed)}
              executionSafetyText={wordpressExecutionSafetyText(actions.executionResult)}
              measurementTitle={data.measurementWindow.outcome_blockers[0]?.label ?? "Nie wolno jeszcze oceniać efektu"}
              measurementSafetyText={measurementSafetyText(window)}
              qualityReview={actions.qualityReview}
              revisionPlan={actions.revisionPlan}
              acfPreviewResult={actions.acfPreviewResult}
            />
          </div>
        ) : null}
      </details>
    </main>
  );
}

function useContentWorkflowActions(
  data: ContentWorkflowSnapshot,
  selectedWorkItemId: string,
  authoringProfile: WordPressAuthoringProfile | null
) {
  const mutations = useContentWorkflowMutations(selectedWorkItemId);
  return contentWorkflowActions(data, mutations, authoringProfile);
}

function useContentWorkflowMutations(selectedWorkItemId: string) {
  const queryClient = useQueryClient();
  const refreshWorkflow = () => {
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "work-item", selectedWorkItemId]
    });
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "wordpress-draft-activation-packet", selectedWorkItemId]
    });
    queryClient.invalidateQueries({
      queryKey: ["content-workflow", "wordpress-draft-write-readiness"]
    });
  };
  const reviewMutation = useMutation({
    mutationFn: (request: ContentWorkItemSnapshotHumanReviewRequest) =>
      saveContentWorkItemSnapshotHumanReview(request, selectedWorkItemId),
    onSuccess: refreshWorkflow
  });
  const auditMutation = useMutation({
    mutationFn: (request: ContentWorkItemSnapshotAuditRequest) =>
      saveContentWorkItemSnapshotAudit(request, selectedWorkItemId),
    onSuccess: refreshWorkflow
  });
  const structuredRuntimeMutation = useMutation({
    mutationFn: postContentWorkItemStructuredDraftRuntime
  });
  const structuredPreviewMutation = useMutation({
    mutationFn: (request: ContentWorkItemStructuredDraftPreviewRequest) =>
      postContentWorkItemStructuredDraftPreview(request, selectedWorkItemId)
  });
  const qualityReviewMutation = useMutation({
    mutationFn: (request: ContentWorkItemQualityReviewRequest) =>
      postContentWorkItemQualityReview(request, selectedWorkItemId)
  });
  const revisionPlanMutation = useMutation({
    mutationFn: (request: ContentWorkItemRevisionPlanRequest) =>
      postContentWorkItemRevisionPlan(request, selectedWorkItemId)
  });
  const acfPreviewMutation = useMutation({
    mutationFn: postContentWorkItemWordPressAuthoringPayloadPreview
  });
  const executionMutation = useMutation({ mutationFn: postContentWorkItemWordPressDraftExecution });
  return {
    reviewMutation,
    auditMutation,
    structuredRuntimeMutation,
    structuredPreviewMutation,
    qualityReviewMutation,
    revisionPlanMutation,
    acfPreviewMutation,
    executionMutation
  };
}

function contentWorkflowActions(
  data: ContentWorkflowSnapshot,
  mutations: ContentWorkflowMutations,
  authoringProfile: WordPressAuthoringProfile | null
) {
  const structuredRuntimeResult = runtimeResultFrom(mutations.structuredRuntimeMutation.data);
  const qualityReview = qualityReviewFrom(mutations.qualityReviewMutation.data);
  return {
    reviewPending: mutations.reviewMutation.isPending,
    auditPending: mutations.auditMutation.isPending,
    structuredRuntimePending: mutations.structuredRuntimeMutation.isPending,
    structuredPreviewPending: mutations.structuredPreviewMutation.isPending,
    qualityReviewPending: mutations.qualityReviewMutation.isPending,
    revisionPlanPending: mutations.revisionPlanMutation.isPending,
    acfPreviewPending: mutations.acfPreviewMutation.isPending,
    executionPending: mutations.executionMutation.isPending,
    authoringProfileReady: Boolean(authoringProfile),
    structuredRuntimeResult,
    structuredPreviewResult: previewResultFrom(mutations.structuredPreviewMutation.data),
    qualityReview,
    revisionPlan: revisionPlanFrom(mutations.revisionPlanMutation.data),
    acfPreviewResult: acfPreviewResultFrom(mutations.acfPreviewMutation.data),
    executionResult: executionResultFrom(mutations.executionMutation.data),
    runStructuredRuntime: () =>
      submitIfReady(structuredRuntimeDryRunRequest(data), mutations.structuredRuntimeMutation.mutate),
    runStructuredPreview: () =>
      submitIfReady(
        structuredPreviewRequest(data, structuredRuntimeResult),
        mutations.structuredPreviewMutation.mutate
      ),
    runQualityReview: () =>
      submitIfReady(
        qualityReviewRequest(data, structuredRuntimeResult),
        mutations.qualityReviewMutation.mutate
      ),
    runRevisionPlan: () =>
      submitIfReady(revisionPlanRequest(data, qualityReview), mutations.revisionPlanMutation.mutate),
    saveReview: () =>
      submitIfReady(
        humanReviewRequest(data, data.draftPackage.draft_package_result.draft_package),
        mutations.reviewMutation.mutate
      ),
    saveAudit: () => submitIfReady(auditRequest(data), mutations.auditMutation.mutate),
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

function workflowControlItems(
  data: ContentWorkflowSnapshot,
  actions: ContentWorkflowActions
): WorkflowControlItem[] {
  const draft = data.draftPackage.draft_package_result.draft_package;
  const review = data.humanReview.review;
  const handoff = data.wordpressHandoff.handoff_result.handoff;
  return [
    {
      label: review ? "Sprawdzenie zapisane" : "Zatwierdź sprawdzenie",
      disabledReason: reviewControlDisabledReason(data, Boolean(draft), actions.reviewPending),
      pending: actions.reviewPending,
      onClick: actions.saveReview
    },
    {
      label: handoff ? "Audyt zapisany" : "Zapisz audyt przekazania",
      disabledReason: auditControlDisabledReason(data, actions.auditPending),
      pending: actions.auditPending,
      onClick: actions.saveAudit
    },
    structuredRuntimeControlItem(data, actions),
    structuredPreviewControlItem(data, actions),
    qualityReviewControlItem(actions),
    revisionPlanControlItem(actions),
    {
      label: actions.acfPreviewResult ? "Mapowanie ACF gotowe" : "Pokaż mapowanie ACF",
      disabledReason: acfPreviewControlDisabledReason(
        Boolean(draft),
        Boolean(handoff),
        actions.authoringProfileReady,
        actions.acfPreviewPending,
        actions.acfPreviewResult
      ),
      pending: actions.acfPreviewPending,
      onClick: actions.runAcfPreview
    },
    {
      label: actions.executionResult ? "Podgląd szkicu gotowy" : "Sprawdź podgląd szkicu",
      disabledReason: executionControlDisabledReason(
        Boolean(draft),
        Boolean(handoff),
        actions.executionPending,
        actions.executionResult
      ),
      pending: actions.executionPending,
      onClick: actions.runExecutionDryRun
    }
  ];
}

function structuredRuntimeControlItem(
  data: ContentWorkflowSnapshot,
  actions: ContentWorkflowActions
): WorkflowControlItem {
  return {
    label: actions.structuredRuntimeResult ? "Próba szkicu gotowa" : "Sprawdź gotowość szkicu",
    disabledReason: structuredRuntimeControlDisabledReason(
      data,
      actions.structuredRuntimePending,
      actions.structuredRuntimeResult
    ),
    pending: actions.structuredRuntimePending,
    onClick: actions.runStructuredRuntime
  };
}

function structuredPreviewControlItem(
  data: ContentWorkflowSnapshot,
  actions: ContentWorkflowActions
): WorkflowControlItem {
  return {
    label: actions.structuredPreviewResult ? "Podgląd treści gotowy" : "Pokaż podgląd treści",
    disabledReason: structuredPreviewControlDisabledReason(
      data,
      actions.structuredPreviewPending,
      actions.structuredPreviewResult,
      actions.structuredRuntimeResult
    ),
    pending: actions.structuredPreviewPending,
    onClick: actions.runStructuredPreview
  };
}

function qualityReviewControlItem(actions: ContentWorkflowActions): WorkflowControlItem {
  return {
    label: actions.qualityReview ? "Ocena jakości gotowa" : "Sprawdź jakość szkicu",
    disabledReason: qualityReviewControlDisabledReason(
      actions.qualityReviewPending,
      actions.qualityReview,
      actions.structuredRuntimeResult
    ),
    pending: actions.qualityReviewPending,
    onClick: actions.runQualityReview
  };
}

function revisionPlanControlItem(actions: ContentWorkflowActions): WorkflowControlItem {
  return {
    label: actions.revisionPlan ? "Plan poprawki gotowy" : "Pokaż plan poprawki",
    disabledReason: revisionPlanControlDisabledReason(
      actions.revisionPlanPending,
      actions.revisionPlan,
      actions.qualityReview
    ),
    pending: actions.revisionPlanPending,
    onClick: actions.runRevisionPlan
  };
}
