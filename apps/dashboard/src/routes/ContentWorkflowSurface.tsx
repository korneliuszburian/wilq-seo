import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useState } from "react";

import { LoadingBand } from "../components/OperatorPrimitives";
import {
  postContentWorkItemCodexSectionProposal,
  getContentWorkItemInitialDraft,
  postContentWorkItemInitialDraft,
  postContentWorkItemSemanticReview,
  postContentWorkItemWordPressAuthoringPayloadPreview,
  postContentWorkItemWordPressDraftExecution,
  saveContentWorkItemDraftRevision,
  saveContentWorkItemDraftRevisionReview,
  saveContentWorkItemPlanningReview,
  type ContentDraftRevision,
  type ContentDraftRevisionDecision,
  type ContentDraftRevisionReviewRequest,
  type ContentDraftRevisionSaveRequest,
  type ContentDraftRevisionSection,
  type ContentPlanningReviewRequest,
  type ContentSemanticReviewResponse,
  type ContentWorkItemQueueResponse,
  type ContentWorkItemWordPressDraftExecutionRequest,
  type ContentOpportunityEnrichment,
  type WordPressAuthoringProfile
} from "../lib/api";
import type { ContentWorkflowSnapshot, WorkflowStepId } from "./contentWorkflowRuntime";
import { ContentCandidateQueuePanel } from "./ContentCandidateQueuePanel";
import { WorkflowStepsList } from "./WorkflowStepsList";
import {
  ContentWorkflowError,
  ContentWorkflowEmptyQueue,
  ContentWorkflowSelectedLoading
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
  type ContentWorkItemQueueQuery,
  type ContentWorkflowSnapshotQuery,
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
export function ContentWorkflowSurface() {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
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
      onSelectWorkItem={selectWorkItem}
    />
  );
}

function stringFromSearch(search: string, key: string) {
  const value = new URLSearchParams(search).get(key);
  return value || null;
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
      key={activeWorkItemId}
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
  const [viewMode, setViewMode] = useState<"marketer" | "technical">("marketer");
  const steps = data.operatorSteps;

  return (
    <main className="w-full px-4 py-3 sm:py-5 lg:px-7 2xl:px-8">
      <section className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-white px-3 py-2 sm:mb-4 sm:px-4 sm:py-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">Widok pracy</p>
          <p className="mt-1 hidden text-sm text-slate-700 sm:block">
            {viewMode === "marketer"
              ? "Decyzja, blocker i następny bezpieczny krok."
              : "Dowody, audyt i kontrakty do sprawdzenia technicznego."}
          </p>
        </div>
        <div className="flex rounded-md border border-line bg-surface p-1" role="group" aria-label="Tryb widoku">
          <button
            type="button"
            aria-pressed={viewMode === "marketer"}
            onClick={() => setViewMode("marketer")}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "marketer" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Marketer
          </button>
          <button
            type="button"
            aria-pressed={viewMode === "technical"}
            onClick={() => setViewMode("technical")}
            className={`rounded px-3 py-2 text-sm font-semibold ${
              viewMode === "technical" ? "bg-white text-action shadow-sm" : "text-slate-600"
            }`}
          >
            Audyt techniczny
          </button>
        </div>
      </section>

      {viewMode === "marketer" ? (
      <ContentWorkflowMarketerJourney
          key={`${selectedWorkItemId}:${data.currentStepId}`}
          actions={actions}
          authoringProfile={authoringProfile}
          data={data}
          draftActivationPacket={draftActivationPacket}
          enrichment={enrichment}
        queue={queue}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
      ) : (
        <section
          id="content-workflow-details"
          aria-label="Audyt techniczny workflow treści"
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
  selectedWorkItemId,
  onSelectWorkItem
}: {
  actions: ContentWorkflowActions;
  authoringProfile: WordPressAuthoringProfileQuery;
  data: ContentWorkflowSnapshot;
  draftActivationPacket: WordPressDraftActivationPacketQuery;
  enrichment: ContentOpportunityEnrichment | null;
  queue: ContentWorkItemQueueResponse;
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
        planningDigest={data.planningWorkspace?.proposal.planning_digest ?? null}
        planningSections={data.planningWorkspace?.proposal.sections ?? []}
        queue={queue}
        selectedWorkItemId={selectedWorkItemId}
        onSelectWorkItem={onSelectWorkItem}
      />
      <ContentWorkflowJourneyContext data={data} />
      <ContentWorkflowTaskMap
        currentStepId={data.currentStepId}
        selectedStepId={selectedStepId}
        steps={data.operatorSteps}
        onSelectStep={selectStep}
      />
      <ContentPageWorkbenchView
        actions={actions}
        authoringProfile={authoringProfile}
        data={data}
        draftActivationPacket={draftActivationPacket}
        enrichment={enrichment}
        queue={queue}
        activeStepId={selectedStepId}
      />
    </div>
  );
}

function ContentSessionPicker({
  planningDigest,
  planningSections,
  queue,
  selectedWorkItemId,
  onSelectWorkItem
}: {
  planningDigest: string | null;
  planningSections: ContentPlanningSections;
  queue: ContentWorkItemQueueResponse;
  selectedWorkItemId: string;
  onSelectWorkItem: (workItemId: string) => void;
}) {
  const navigate = useNavigate();
  const routeSearch = useRouterState({ select: (state) => state.location.searchStr });
  const requestedSectionHeading = stringFromSearch(routeSearch, "section_heading");
  const requestedPlanningDigest = stringFromSearch(routeSearch, "planning_digest");
  const candidates = queue.candidates.filter(
    (candidate) => candidate.recommended_mode !== "block"
  );
  const selected = candidates.find(
    (candidate) => candidate.work_item_id === selectedWorkItemId
  );
  const selectedSection =
    (requestedPlanningDigest === planningDigest
      ? planningSections.find((section) => section.heading === requestedSectionHeading)
      : null) ??
    planningSections[0] ??
    null;
  if (!selected) return null;

  return (
    <section
      aria-labelledby="content-session-picker-title"
      className="mb-3 rounded-md border border-line bg-white px-3 py-3 sm:mb-4 sm:px-4"
      data-testid="content-session-picker"
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(15rem,22rem)_minmax(15rem,22rem)] lg:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">
            Początek sesji
          </p>
          <h2 id="content-session-picker-title" className="mt-1 text-lg font-semibold text-ink">
            Wybierz stronę do pracy
          </h2>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            WILQ pokazuje tylko strony z dowodami i sprawdzonym adresem. Wybór zmienia cały
            pięciostopniowy przebieg poniżej.
          </p>
        </div>
        <label className="text-sm font-semibold text-ink" htmlFor="content-session-work-item">
          Strona i temat
          <select
            id="content-session-work-item"
            className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink"
            value={selectedWorkItemId}
            onChange={(event) => onSelectWorkItem(event.target.value)}
          >
            {candidates.map((candidate) => (
              <option key={candidate.work_item_id} value={candidate.work_item_id}>
                {candidate.topic} — {contentCandidatePath(candidate.final_canonical_url)}
              </option>
            ))}
          </select>
        </label>
        {selectedSection ? (
          <label className="text-sm font-semibold text-ink" htmlFor="content-session-section">
            Sekcja do pracy
            <select
              id="content-session-section"
              className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2 font-normal text-ink"
              value={selectedSection.heading}
              onChange={(event) => {
                void navigate({
                  to: "/content-workflow",
                  search: (previous) => ({
                    ...previous,
                    work_item_id: selectedWorkItemId,
                    section_heading: event.target.value,
                    planning_digest: planningDigest ?? undefined
                  }),
                  replace: true
                });
              }}
            >
              {planningSections.map((section) => (
                <option key={section.heading} value={section.heading}>
                  {section.heading}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      <p className="mt-2 text-xs text-slate-500">
        {selected.recommended_mode_label} · {selected.evidence_ids.length} źródła dowodowe
        {selectedSection ? ` · Fokus: ${selectedSection.heading}` : ""}
      </p>
    </section>
  );
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
  authoringProfile: WordPressAuthoringProfile | null
) {
  const mutations = useContentWorkflowMutations(selectedWorkItemId);
  return contentWorkflowActions(data, mutations, authoringProfile);
}

function useContentWorkflowMutations(selectedWorkItemId: string) {
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
          requested_by: "wilku"
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
          requested_by: "wilku"
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
    enabled: initialDraftMutation.data?.status === "generating",
    refetchInterval: (query) =>
      query.state.data?.status === "generating" ? 2000 : false
  });
  const semanticReviewMutation = useMutation({
    mutationFn: ({ revisionId, revisionDigest }: { revisionId: string; revisionDigest: string }) =>
      postContentWorkItemSemanticReview(
        {
          expected_revision_digest: revisionDigest,
          requested_by: "wilku"
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
  authoringProfile: WordPressAuthoringProfile | null
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
        reviewed_by: "wilku",
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
    initialDraftResult: mutations.initialDraftMutation.data ?? null,
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
          reviewed_by: "wilku",
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
